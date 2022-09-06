"""
This module defines the UI handler class, which is where all the magic happens.
"""
import shutil
import signal
import sys
import tempfile
import termios
import threading
import time
import tty
from pathlib import Path

import chardet
import magic
from blessed import Terminal

from .alignment import Dimension, TopLeftAnchor
from .block import Block
from .common import Commons
from .control import Control
from .screen import Screen

FRAMERATE = 0.02
"""
Defines at most how often should a new frame be generated, in seconds. This is a terminal application, we really don't need more than 50 FPS.
"""


class ControlCodes:
    """
    Enum for available CTRL codes. See the documentation of awsc.termui.control.HotkeyControl.add_hotkey on how to use these.
    """

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
    """
    Debug control for displaying the key being pressed. Input function of this control does not consume the key.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes a KeyDisplay object.
        """
        super().__init__(*args, **kwargs)
        self.text = "<no key>"

    def input(self, key):
        if key.is_sequence:
            self.text = f"{(str(key), key.name, key.code)}"
        else:
            self.text = key
        return False

    def paint(self):
        super().paint()
        topleft = self.topleft()
        Commons.UIInstance.print(self.text, xy=topleft)


class UI:
    """
    UI singleton object. Handles the main loop of a termui application.

    Attributes
    ----------
    debug : int
        Debug level. Should be unused most of the time.
    top_block : awsc.termui.block.Block
        The topmost block which spans the screen. Should be used as the parent of all top level blocks displayed on the screen.
    last_paint : time.Time
        Timer tracking when the last paint event occurred.
    last_size_refresh : time.Time
        Timer tracking when the last refresh of screen size occurred. Screen size refresh is an expensive operation for some reason.
    term : blessed.Terminal
        The blessed Terminal that is being operated on.
    _w : int
        The width of the terminal in characters. Eventually consistent value, only changes on screen size refresh.
    _h : int
        The height of the terminal in characters. Eventually consistent value, only changes on screen size refresh.
    exit : bool
        If set, the program will exit on the next cycle of the main loop.
    buf : awsc.termui.screen.Screen
        The screen buffer that is manipulated in paint operations. Each control outputting directly to the screen is expensive and
        error prone. Manipulating a buffer and printing it all at once is significantly faster.
    tickers : list(callable)
        A list of hooks to execute on each main loop cycle.
    cache_dir : str
        A file cache temporary directory. Ideally erased upon graceful shutdown, with all of its contents.
    mutex : threading.Lock
        Controls access to the input buffer.
    input_buffer : list(blessed.keyboard.Keystroke)
        A list of unprocessed keyboard inputs. Handled in the event loop.
    dirty : bool
        Whether the UI requires a repaint.
    restore : object
        Stores the state of the terminal to restore to upon shutdown. Required to return the user to a working terminal after exiting.
    """

    def __init__(self):
        """
        Initializes a UI object.
        """
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

    @staticmethod
    def read_file(filename):
        """
        Reads a file in the correct encoding, or binary mode if mime type does not indicate it is a text file.

        Parameters
        ----------
        filename : str or pathlib.Path
            The name of the file.

        Returns
        -------
        str or bytes
            The contents of the file.
        """
        mime = magic.from_file(filename)
        filename = str(filename)
        with open(filename, "rb") as file:
            data = file.read()
        # Do not even try to decode common binary format mime types.
        if not mime.startswith("text/"):
            return data
        result = chardet.detect(data)
        # Arbitrary lower limit for confidence.
        if result["confidence"] >= 0.7:
            return data.decode(result["encoding"])
        return data

    def filecache(self, obj, callback, *args, **kwargs):
        """
        Retrieves a cached file from the temporary file cache. If the file is not present, the callback is called to retrieve the cached file.

        Parameters
        ----------
        obj : str
            The name of the cached file to retrieve.
        callback : callable(str, *args, **kwargs) -> str or bytes
            A callback that is used to fetch the file contents if it is not cached. The callback, for now, is expected to cache the file
            itself so that it can be fetched from cache later. The callback is passed the full path where the file should be cached, as well
            as all additional positional and keyword arguments this function receives and should return the contents of the file as str or
            bytes, depending on whether it's a text or binary file.
        *args : list
            A list of additional positional arguments to pass to the callback.
        **kwargs : dict
            A dict of additional keyword arguments to pass to the callback.

        Returns
        -------
        str or bytes
            The contents of the cached file.
        """
        objpath = self.filecache_path(obj, callback, *args, **kwargs)
        return self.read_file(objpath)

    def filecache_path(self, obj, callback, *args, **kwargs):
        """
        Like filecache, except this one only returns the path of the cached file. Useful if you don't want to decode and recode the file.

         Parameters
        ----------
        obj : str
            The name of the cached file to retrieve.
        callback : callable(str, *args, **kwargs) -> str or bytes
            A callback that is used to fetch the file contents if it is not cached. The callback, for now, is expected to cache the file
            itself so that it can be fetched from cache later. The callback is passed the full path where the file should be cached, as well
            as all additional positional and keyword arguments this function receives and should return the contents of the file as str or
            bytes, depending on whether it's a text or binary file.
        *args : list
            A list of additional positional arguments to pass to the callback.
        **kwargs : dict
            A dict of additional keyword arguments to pass to the callback.

        Returns
        -------
        pathlib.Path
            The path to the file.
        """
        if self.cache_dir is None:
            self.cache_dir = tempfile.mkdtemp(prefix="awsc")
        objpath = Path(self.cache_dir) / obj
        if not objpath.exists():
            callback(str(objpath.resolve()), *args, **kwargs)
        return objpath

    def print(self, out, xy=None, color=None, wrap=False, bounds=None, bold=False):
        """
        Prints a text to a specified area of the screen buffer. Has no real effect if called outside the block paint hooks.

        Parameters
        ----------
        out : str
            The string to print on the screen.
        xy : tuple(int, int), optional
            Where to print on the screen. If omitted, prints to the top left corner of the bounding box.
        color : awsc.termui.color.Color, optional
            A callable which takes a string and returns a string. Used as a callback to color the output string.
        wrap : bool, default=False
            If set, text will wrap within the bounding box. Otherwise, the overflow on the row of the text is cut off.
        bounds : tuple(int, int), optional
            The bounding box for printing the text. If omitted, the bounding box is the entire terminal.
        bold : bool, default=False
            If set, prints the text in bold.
        """
        if color is not None and not callable(color):
            raise ValueError("Color must be callable or None.")
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
        """
        Refreshes the cached width and height of the terminal if it has not been refreshed recently.

        Based on profiling, retrieving the blessed terminal width and height is a rather expensive operation, which is why this is
        strictly rate limited and cached. Besides, the user is very unlikely to repeatedly and rapidly resize the terminal.
        """
        if self.last_paint - self.last_size_refresh > 1:
            self.last_size_refresh = self.last_paint
            self._w = self.term.width
            self._h = self.term.height

    @property
    def width(self):
        """
        Read-only property for the width of the terminal. Refreshes the value of _w and _h if necessary.

        Returns
        -------
        int
            The width of the terminal.
        """
        self.refresh_size()
        return self._w

    @property
    def height(self):
        """
        Read-only property for the height of the terminal. Refreshes the value of _w and _h if necessary.

        Returns
        -------
        int
            The height of the terminal.
        """
        self.refresh_size()
        return self._h

    @property
    def dim(self):
        """
        Read-only property for the dimensions of the terminal. Refreshes the value of _w and _h if necessary.

        Returns
        -------
        tuple(int, int)
            The width and height of the terminal.
        """
        self.refresh_size()
        return (self._w, self._h)

    def set_exit(self, *args, **kwargs):
        """
        Hotkey-compatible function that sets the graceful shutdown flag on the UI.

        Parameters
        ----------
        *args : list
            Unused.
        **kwargs : dict
            Unused.
        """
        self.exit = True

    def before_paint(self):
        """
        Pre-paint hook for the UI. Executes the pre-paint hooks of all blocks within the UI.
        """
        self.top_block.before_paint()

    def progress_bar_paint(self, perc):
        """
        Convenience function for painting a progress bar. The progress bar is painted on the bottom row of the terminal.

        Has no effect if called outside of the paint hooks of blocks.s

        Parameters
        ----------
        perc : float
            The percentage of the progress bar to fill. Should be between 0 and 1, inclusive, for sanity's sake.
        """
        width = int(self.width * perc)
        with self.term.location(0, self.height - 1):
            percentage = perc * 100
            perc_t = f"{percentage:.2f}% "
            print(
                "\033[38;5;220m" + perc_t + ((width - len(perc_t)) * "░") + "\033[0m",
                end="",
            )

    def check_one_key(self):
        """
        Retrieves a single keystroke within a timeout half a frame. The polling time is intentionally short so the keyboard event hook does not
        delay the main loop by a significant degree if no keys are being pressed.

        Returns
        -------
        blessed.keyboard.Keystroke
            A keystroke, if a keystroke happened, or None if no keystrokes happened.
        """
        return self.term.inkey(FRAMERATE / 2.0, FRAMERATE / 2.0)

    def paint(self):
        """
        Main paint handler of the UI. Clears the screen buffer and prompts all blocks within the UI to be painted.
        """
        self.buf.clear()
        self.top_block.paint()
        with self.term.location(0, 0):
            self.buf.output()
        self.last_paint = time.time()
        self.dirty = False

    # TODO: Check BUG documented in the doc.
    def unraw(self, cmd, *args, **kwargs):
        """
        Runs a callback in a default terminal setting. Required to run external commands such as nano or vi in a way that the user
        would expect.

        KNOWN BUG: For some reason, a single keypress erroneously has its control character (^) consumed but the rest of the sequence is
        output if a key is pressed roughly 1 second after the callback is executed. No amount of flushing fixes this. It is probably that
        in some way, the input buffer loop is interfering with this and should be suspended while the unraw command is executing.
        It's annoying but not breaking anything, but does require attention at some point.

        Parameters
        ----------
        cmd : callable
            The function to call after resetting the terminal settings.
        *args : list
            A list of positional arguments to pass to the command.
        **kwargs : dict
            A map of keyword arguments to pass to the command.
        """
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
        """
        Input buffer loop. Runs on a separate thread, listens for keystrokes and pushes them into the input buffer as they become available.

        Actual handling of the inputs happens on the main loop thread.
        """
        while True:
            key = self.term.inkey(None, FRAMERATE / 2)
            if key is not None and key != "":
                with self.mutex:
                    self.input_buffer.append(key)

    def process_input_buffer(self, start_time):
        """
        Processes part of the input buffer. The input buffer will not process any inputs within the final 10ms of its allowed frame time.

        Parameters
        ----------
        start_time: time.Time
            The exact time when the frame processing started.
        """
        with self.mutex:
            if len(self.input_buffer) > 0:
                key = self.input_buffer[0]
                self.input_buffer = self.input_buffer[1:]
                if key == "\x03":
                    raise KeyboardInterrupt
                self.top_block.input(key)
                curr_time = time.time()
                if curr_time - start_time > FRAMERATE - 0.02:
                    return

    def main(self):
        """
        Main loop function of the UI. Call this after setting up your application.

        The main loop function will configure the terminal to use raw inputs, start up the keyboard buffer loop, then runs until the graceful
        shutdown flag is set in an infinite loop. Within this loop, in each cycle, first, the input buffer is processed, then a new frame is
        rendered.
        """
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
