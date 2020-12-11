class Palette:
  def __init__(self):
    pass

  def __call__(self, code, string, bold=False):
    return string

class Palette8Bit(Palette):
  def __call__(self, code, string, background=None, bold=False):
    if not bold:
      ccode = "\033[38;5;{0}m".format(code)
    else:
      ccode = "\033[1;38;5;{0}m".format(code)
    if background is not None:
      ccode = "\033[48;5;{0}m{1}".format(background, ccode)
    return "{0}{1}\033[0m".format(ccode, string)

class Color:
  def __init__(self, palette, code, background=None):
    self.palette = palette
    self.code = code
    self.background = background

  def __call__(self, string, bold=False):
    return self.palette(self.code, string, background=self.background, bold=bold)

ColorBlack = Color(Palette8Bit(), 0)
ColorWhite = Color(Palette8Bit(), 15)
ColorWhiteOnBlack = Color(Palette8Bit(), 15, background=0)
ColorBlackOnWhite = Color(Palette8Bit(), 0, background=15)
ColorGold = Color(Palette8Bit(), 220)
ColorGreen = Color(Palette8Bit(), 40)
ColorGreen = Color(Palette8Bit(), 40)
ColorMagenta = Color(Palette8Bit(), 165)
ColorBlackOnGold = Color(Palette8Bit(), 0, background=220)
ColorBlackOnOrange = Color(Palette8Bit(), 0, background=208)
ColorBlackOnGray = Color(Palette8Bit(), 0, background=251)