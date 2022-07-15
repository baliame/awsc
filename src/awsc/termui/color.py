class Palette:
    def __init__(self):
        pass

    def __call__(self, code, string, bold=False):
        return string


class Palette8Bit(Palette):
    def __call__(self, code, string, background=None, bold=False):
        out = ""
        if background is not None:
            out += "\033[48;5;" + str(background) + "m"
        out += "\033["
        if bold:
            out += "1;"
        out += "38;5;" + str(code) + "m" + string + "\033[0m"
        return out


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
ColorDarkGreen = Color(Palette8Bit(), 70)
ColorMagenta = Color(Palette8Bit(), 165)
ColorBlackOnGold = Color(Palette8Bit(), 0, background=220)
ColorBlackOnOrange = Color(Palette8Bit(), 0, background=208)
ColorBlackOnGray = Color(Palette8Bit(), 0, background=251)
