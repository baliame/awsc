from .color import Color

class Character:
  def __init__(self):
    self.value = ' '
    self.color = None
    self.bold = False

  def output(self):
    o = self.value
    if self.color is not None:
      o = self.color(o, bold=self.bold)
    return o

class Screen:
  def __init__(self, ui):
    self.ui = ui
    self.clear()

  class Row:
    def __init__(self, screen):
      self.screen = screen
      self.clear()

    def clear(self):
      self.buf = [Character() for i in range(self.screen.ui.w)]

    def __getitem__(self, i):
      return self.buf[i]

    def output(self):
      return ''.join(x.output() for x in self.buf)

  def clear(self):
    self.buf = [Screen.Row(self) for i in range(self.ui.h)]

  def __getitem__(self, i):
    return self.buf[i]

  def output(self):
    print('\r\n'.join(x.output() for x in self.buf), end='')