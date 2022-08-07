import shutil
import signal
import sys
import tempfile
import termios
import threading
import time
import tty
from pathlib import Path

from blessed import Terminal

from .alignment import Dimension, TopLeftAnchor
from .block import Block
from .common import Commons
from .control import Control
from .screen import Screen

FRAMERATE = 0.02


class ControlCodes:
    A = "\x01"
    B = "\x02"
    C = "\x03"
    D = "\x04"
    E = "\x05"
    F = "\x06"
    G = "\x07"
    K = "\x0b"
    L = "\x0c"
    M = "\x0d"
    N = "\x0e"
    O = "\x0f"
    P = "\x10"
    Q = "\x11"
    R = "\x12"
    S = "\x13"
    T = "\x14"
    U = "\x15"
    V = "\x16"
    W = "\x17"
    X = "\x18"
    Y = "\x19"
    Z = "\x1a"


class KeyDisplay(Control):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = "<no key>"

    def input(self, key):
        if key.is_sequence:
            self.text = f"{(str(key), key.name, key.code)}"
        else:
            self.text = key

    def paint(self):
        super().paint()
        topleft = self.topleft()
        Commons.UIInstance.print(self.text, xy=topleft)


class UI:
    def __init__(self):
        if Commons.UIInstance is not None:
            raise RuntimeError("UI is a singleton.")
        Commons.UIInstance = self
        self.debug = 1
        self.top_block = Block(
            None, TopLeftAnchor(0, 0), Dimension("100%", "100%"), tag="top"
        )
        self.last_paint = time.time()
        self.last_size_refresh = time.time()
        self.term = Terminal()
        self._w = self.term.width
        self._h = self.term.height
        self.exit = False
        signal.signal(signal.SIGINT, self.set_exit)
        self.buf = Screen(self)
        self.tickers = []
        self.cache_dir = None
        self.mutex = threading.Lock()
        self.input_buffer = []
        self.dirty = False
        self.restore = None

    def filecache(self, obj, callback, *args, **kwargs):
        if self.cache_dir is None:
            self.cache_dir = tempfile.mkdtemp(prefix="awsc")
        objpath = Path(self.cache_dir) / obj
        if not objpath.exists():
            data = callback(str(objpath.resolve()), *args, **kwargs)
            return data
        try:
            with objpath.open("r", encoding="utf-8") as file:
                return file.read()
        except UnicodeDecodeError:
            with objpath.open("rb") as file:
                return file.read()

    def print(self, out, xy=None, color=None, wrap=False, bounds=None, bold=False):
        self.dirty = True
        if bounds is None:
            bounds = ((0, self.width), (0, self.height))
        if xy is None:
            xy = (bounds[0][0], bounds[1][0])
        end = False
        if (xy[0] > bounds[0][1] and not wrap) or xy[1] > bounds[1][1]:
            return
        while not end:
            space = bounds[0][1] - xy[0]
            if len(out) > space:
                part = out[:space]
                out = out[space:]
            else:
                space = len(out)
                part = out
                out = ""
                end = True
            position = 0
            for i in range(xy[0], xy[0] + space):
                try:
                    char = self.buf[xy[1]][i]
                    char.value = part[position]
                    char.color = color
                    char.bold = bold
                    char.dirty = True
                except IndexError:
                    break
                position += 1
            xy = (bounds[0][0], xy[1] + 1)
            if not wrap or xy[1] >= bounds[1][1]:
                end = True

    def refresh_size(self):
        if self.last_paint - self.last_size_refresh > 1:
            self.last_size_refresh = self.last_paint
            self._w = self.term.width
            self._h = self.term.height

    @property
    def width(self):
        self.refresh_size()
        return self._w

    @property
    def height(self):
        self.refresh_size()
        return self._h

    @property
    def dim(self):
        self.refresh_size()
        return (self._w, self._h)

    def set_exit(self, *args, **kwargs):
        self.exit = True

    def before_paint(self):
        self.top_block.before_paint()

    def progress_bar_paint(self, perc):
        width = int(self.width * perc)
        with self.term.location(0, self.height - 1):
            percentage = perc * 100
            perc_t = f"{percentage:.2f}% "
            print(
                "\033[38;5;220m" + perc_t + ((width - len(perc_t)) * "░") + "\033[0m",
                end="",
            )

    def check_one_key(self):
        return self.term.inkey(0.01, 0.01)

    def paint(self):
        self.buf.clear()
        self.top_block.paint()
        with self.term.location(0, 0):
            self.buf.output()
        self.last_paint = time.time()
        self.dirty = False

    def unraw(self, cmd, *args, **kwargs):
        # termios.tcsetattr(self.term._keyboard_fd, termios.TCSAFLUSH, self.restore)
        # pylint: disable=protected-access
        termios.tcsetattr(self.term._keyboard_fd, termios.TCSANOW, self.restore)
        # pylint: disable=protected-access
        self.term._line_buffered = True
        self.term.stream.write(self.term.normal_cursor)
        self.term.stream.flush()
        self.term.stream.write(self.term.exit_fullscreen)
        self.term.stream.flush()
        termios.tcflush(sys.stdin, termios.TCIOFLUSH)
        try:
            return cmd(*args, **kwargs)
        finally:
            self.term.stream.write(self.term.enter_fullscreen)
            self.term.stream.flush()
            self.term.stream.write(self.term.hide_cursor)
            self.term.stream.flush()
            # pylint: disable=protected-access
            tty.setraw(self.term._keyboard_fd, termios.TCSANOW)
            # pylint: disable=protected-access
            self.term._line_buffered = False

    def buffer_input(self):
        while True:
            key = self.term.inkey(None, 0.01)
            if key is not None and key != "":
                self.mutex.acquire()
                try:
                    self.input_buffer.append(key)
                finally:
                    self.mutex.release()

    def process_input_buffer(self, start_time):
        self.mutex.acquire()
        try:
            if len(self.input_buffer) > 0:
                key = self.input_buffer[0]
                self.input_buffer = self.input_buffer[1:]
                if key == "\x03":
                    raise KeyboardInterrupt
                self.top_block.input(key)
                curr_time = time.time()
                if curr_time - start_time > FRAMERATE - 0.02:
                    return
        finally:
            self.mutex.release()

    def main(self):
        # pylint: disable=protected-access
        self.restore = termios.tcgetattr(self.term._keyboard_fd)
        try:
            with self.term.fullscreen():
                with self.term.hidden_cursor():
                    with self.term.raw():
                        thread = threading.Thread(target=self.buffer_input, daemon=True)
                        thread.start()
                        while not self.exit:
                            # print(self.term.clear())
                            start_time = time.time()
                            self.process_input_buffer(start_time)
                            for func in self.tickers:
                                func()
                            self.before_paint()
                            if self.dirty or time.time() - self.last_paint > 3:
                                self.paint()
                            curr_time = time.time()
                            delay = FRAMERATE - (curr_time - start_time)
                            if delay > 0:
                                time.sleep(delay)
        except KeyboardInterrupt:
            pass
        finally:
            if self.cache_dir is not None:
                shutil.rmtree(self.cache_dir)
