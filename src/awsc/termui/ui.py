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

FrameRate = 0.02


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
            self.text = "{0}".format((str(key), key.name, key.code))
        else:
            self.text = key

    def paint(self):
        super().paint()
        tl = self.topleft()
        Commons.UIInstance.print(self.text, xy=tl)


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

    def filecache(self, obj, cb, *args, **kwargs):
        if self.cache_dir is None:
            self.cache_dir = tempfile.mkdtemp(prefix="awsc")
        objpath = Path(self.cache_dir) / obj
        if not objpath.exists():
            data = cb(str(objpath.resolve()), *args, **kwargs)
            return data
        try:
            with objpath.open("r") as f:
                return f.read()
        except UnicodeDecodeError:
            with objpath.open("rb") as f:
                return f.read()

    def print(self, out, xy=None, color=None, wrap=False, bounds=None, bold=False):
        self.dirty = True
        if bounds is None:
            bounds = ((0, self.w), (0, self.h))
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
            p = 0
            for i in range(xy[0], xy[0] + space):
                try:
                    char = self.buf[xy[1]][i]
                    char.value = part[p]
                    char.color = color
                    char.bold = bold
                    char.dirty = True
                except IndexError:
                    break
                p += 1
            xy = (bounds[0][0], xy[1] + 1)
            if not wrap or xy[1] >= bounds[1][1]:
                end = True

    def refresh_size(self):
        if self.last_paint - self.last_size_refresh > 1:
            self.last_size_refresh = self.last_paint
            self._w = self.term.width
            self._h = self.term.height

    @property
    def w(self):
        self.refresh_size()
        return self._w

    @property
    def h(self):
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
        width = int(self.w * perc)
        with self.term.location(0, self.h - 1):
            perc_t = "{0:.2f}% ".format(perc * 100)
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
        termios.tcsetattr(self.term._keyboard_fd, termios.TCSANOW, self.restore)
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
            tty.setraw(self.term._keyboard_fd, termios.TCSANOW)
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

    def process_input_buffer(self, st):
        self.mutex.acquire()
        try:
            if len(self.input_buffer) > 0:
                key = self.input_buffer[0]
                self.input_buffer = self.input_buffer[1:]
                if key == "\x03":
                    raise KeyboardInterrupt
                self.top_block.input(key)
                ct = time.time()
                if ct - st > FrameRate - 0.02:
                    return
        finally:
            self.mutex.release()

    def main(self):
        global FrameRate
        self.restore = termios.tcgetattr(self.term._keyboard_fd)
        try:
            with self.term.fullscreen():
                with self.term.hidden_cursor():
                    with self.term.raw():
                        t = threading.Thread(target=self.buffer_input, daemon=True)
                        t.start()
                        while not self.exit:
                            # print(self.term.clear())
                            st = time.time()
                            self.process_input_buffer(st)
                            for func in self.tickers:
                                func()
                            self.before_paint()
                            if self.dirty or time.time() - self.last_paint > 3:
                                self.paint()
                            t2 = time.time()
                            d = FrameRate - (t2 - st)
                            if d > 0:
                                time.sleep(d)
        except KeyboardInterrupt:
            pass
        finally:
            if self.cache_dir is not None:
                shutil.rmtree(self.cache_dir)
