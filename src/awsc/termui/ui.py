import curses
from blessed import Terminal
import termios
import tty
import signal
import time
from .alignment import TopLeftAnchor, Dimension, CenterAnchor
from .common import Commons
from .control import Control, Border, BorderStyleContinuous
from .list_control import ListControl, ListEntry
from .dialog import DialogControl, DialogFieldLabel, DialogFieldText
from .color import ColorGold, ColorGreen, ColorMagenta
from .block import Block
import numpy as np
from .screen import Screen
import shutil
import tempfile
from pathlib import Path

FrameRate = 0.05

class ControlCodes:
  A = '\x01'
  B = '\x02'
  C = '\x03'
  D = '\x04'
  E = '\x05'
  F = '\x06'
  G = '\x07'
  K = '\x0b'
  L = '\x0c'
  M = '\x0d'
  N = '\x0e'
  O = '\x0f'
  P = '\x10'
  Q = '\x11'
  R = '\x12'
  S = '\x13'
  T = '\x14'
  U = '\x15'
  V = '\x16'
  W = '\x17'
  X = '\x18'
  Y = '\x19'
  Z = '\x1a'

class KeyDisplay(Control):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.text = '<no key>'

  def input(self, key):
    if key.is_sequence:
      self.text = '{0}'.format((str(key), key.name, key.code))
    else:
      self.text = key

  def paint(self):
    super().paint()
    tl = self.topleft()
    Commons.UIInstance.print(self.text, xy=tl)

class UI:
  def __init__(self):
    if Commons.UIInstance is not None:
      raise RuntimeError('UI is a singleton.')
    Commons.UIInstance = self
    self.debug = 1
    self.clear_log()
    self.top_block = Block(None, TopLeftAnchor(0, 0), Dimension('100%', '100%'), tag='top')
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

  def clear_log(self):
    if self.debug == 0:
      return
    with open('log.log', 'w') as f:
      pass

  def log(self, line, level=1):
    if self.debug < level:
      return
    with open('log.log', 'a') as f:
      f.write(line)
      f.write('\n')

  def filecache(self, obj, cb, *args, **kwargs):
    if self.cache_dir is None:
      self.cache_dir = tempfile.mkdtemp(prefix='awsc')
    objpath = Path(self.cache_dir) / obj
    if not objpath.exists():
      data = cb(str(objpath.resolve()), *args, **kwargs)
      return data
    try:
      with objpath.open('r') as f:
        return f.read()
    except UnicodeDecodeError:
      with objpath.open('rb') as f:
        return f.read()

  def print(self, out, xy=None, color=None, wrap=False, bounds=None, bold=False):
    if bounds is None:
      bounds = ((0, self.w), (0, self.h))
    if xy is None:
      xy = (bounds[0][0], bounds[1][0])
    end = False
    while not end:
      space = bounds[0][1] - xy[0]
      if len(out) > space:
        part = out[:space]
        out = out[space:]
      else:
        space = len(out)
        part = out
        out = ''
        end = True
      p = 0
      self.log('UI: Print string on screen size [{0} {1}] | Space in line: {2} | Part to print: {3} ({4})'.format(self.w, self.h, space, len(part), part), level=4)
      for i in range(xy[0], xy[0]+space):
        self.log('Printing to [{0} {1}] character {2} of {3}'.format(xy[1], i, p, part), level=4)
        try:
          self.buf[xy[1]][i].value = part[p]
          if color is not None:
            self.buf[xy[1]][i].color = color
          self.buf[xy[1]][i].bold = bold
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
      perc_t = '{0:.2f}% '.format(perc * 100)
      print('\033[38;5;220m' + perc_t + ((width - len(perc_t)) * '░') + '\033[0m', end='')

  def check_one_key(self):
    return self.term.inkey(FrameRate / 8, FrameRate / 8)

  def paint(self):
    row = ' ' * self.w
    self.buf.clear()
    self.top_block.paint()
    with self.term.location(0, 0):
      self.buf.output()
    self.last_paint = time.time()

  def unraw(self, cmd, *args, **kwargs):
    termios.tcsetattr(self.term._keyboard_fd, termios.TCSAFLUSH, self.restore)
    self.term._line_buffered = True
    self.term.stream.write(self.term.normal_cursor)
    self.term.stream.flush()
    self.term.stream.write(self.term.exit_fullscreen)
    self.term.stream.flush()
    try:
      return cmd(*args, **kwargs)
    finally:
      self.term.stream.write(self.term.enter_fullscreen)
      self.term.stream.flush()
      self.term.stream.write(self.term.hide_cursor)
      self.term.stream.flush()
      tty.setraw(self.term. _keyboard_fd, termios.TCSANOW)
      self.term._line_buffered = False

  def main(self):
    global FrameRate
    self.restore = termios.tcgetattr(self.term._keyboard_fd)
    try:
      with self.term.fullscreen():
        with self.term.hidden_cursor():
          with self.term.raw():
            while not self.exit:
              #print(self.term.clear())
              st = time.time()
              for func in self.tickers:
                func()
              self.before_paint()
              self.paint()
              while key := self.term.inkey(FrameRate / 4, FrameRate / 4):
                if key == '\x03':
                  raise KeyboardInterrupt
                self.top_block.input(key)
                ct = time.time()
                if ct - st > FrameRate:
                  break
              t2 = time.time()
              self.log('Frame time: {0}'.format(t2 - st), level=1)
              d = FrameRate - (t2 - st)
              if d > 0:
                time.sleep(d)
    except KeyboardInterrupt:
      pass
    finally:
      if self.cache_dir is not None:
        shutil.rmtree(self.cache_dir)
