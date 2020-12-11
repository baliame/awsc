import curses
from blessed import Terminal
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
    self.term = Terminal()
    self.exit = False
    signal.signal(signal.SIGINT, self.set_exit)
    self.buf = Screen(self)
    self.tickers = []

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
      self.log('UI: Print string on screen size [{0} {1}] | Space in line: {2} | Part to print: {3} ({4})'.format(self.w, self.h, space, len(part), part), level=3)
      for i in range(xy[0], xy[0]+space):
        self.log('Printing to [{0} {1}] character {2} of {3}'.format(xy[1], i, p, part), level=3)
        self.buf[xy[1]][i].value = part[p]
        if color is not None:
          self.buf[xy[1]][i].color = color
        self.buf[xy[1]][i].bold = bold
        p += 1
      xy = (bounds[0][0], xy[1] + 1)
      if not wrap or xy[1] >= bounds[1][1]:
        end = True

  @property
  def w(self):
    return self.term.width

  @property
  def h(self):
    return self.term.height

  @property
  def dim(self):
    return (self.w, self.h)

  def set_exit(self, *args, **kwargs):
    self.exit = True

  def paint(self):
    row = ' ' * self.w
    self.buf.clear()
    self.top_block.paint()
    with self.term.location(0, 0):
      self.buf.output()

  def main(self):
    global FrameRate
    try:
      with self.term.fullscreen():
        with self.term.hidden_cursor():
          with self.term.raw():
            while not self.exit:
              #print(self.term.clear())
              st = time.time()
              for func in self.tickers:
                func()
              self.paint()
              key = self.term.inkey(FrameRate, FrameRate)
              if key:
                if key == '\x03':
                  raise KeyboardInterrupt
                self.top_block.input(key)
              t2 = time.time()
              self.log('Frame time: {0}'.format(t2 - st), level=2)
              d = FrameRate - (t2 - st)
              if d > 0:
                time.sleep(d)
    except KeyboardInterrupt:
      print('Exit.')
