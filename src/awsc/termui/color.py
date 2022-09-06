"""
This module defines classes that allow simply coloring text on terminals.
"""


class Palette:
    """
    Palette base class.

    A palette is expected to be able to colorize a string in a certain terminal format based on a foreground color code,
    a background color code, and optionally, a boldness flag.
    """

    def __call__(self, code, string, background=None, bold=False):
        """
        Colorize a string.

        Parameters
        ----------
        code : object
            The color code of the foreground color. Palette implementation decides how to handle this code.
        string : str
            The string to colorize.
        background : object, optional
            The color code of the background color, or default if omitted.
        bold : bool
            Whether to bolden the string.

        Returns
        -------
        str
            The string, with the appropriate escape sequences embedded to set the color at the beginning of the string and to reset at the end.
        """
        return string


class Palette8Bit(Palette):
    """
    Palette8Bit uses the ANSI 38;5;n and 48;5;n format to access the 256 color table.
    """

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
    """
    A Color is a specific code in a palette. Color objects can be used to quickly colorize strings.

    Attributes
    ----------
    palette : awsc.termui.color.Palette
        The Palette where this color can be found.
    code : object
        The code of the foreground color associated with this color in the palette.
    background : object
        The code of the background color associated with this color in the palette. If None, the color of the background should not be changed.
    """

    def __init__(self, palette, code, background=None):
        """
        Initializes a Color object.

        Parameters
        ----------
        palette : awsc.termui.color.Palette
            The Palette where this color can be found.
        code : object
            The code of the foreground color associated with this color in the palette.
        background : object, optional
            The code of the background color associated with this color in the palette. If None, the color of the background should not be changed.
        """
        self.palette = palette
        self.code = code
        self.background = background

    def __str__(self):
        return f"{type(self.palette).__name__}:{self.code},{self.background}"

    def __repr__(self):
        return f"{type(self).__name__}({type(self.palette).__name__}, {self.code}, {self.background})"

    def __call__(self, string, bold=False):
        """
        Colorize a string with this Color.

        Parameters
        ----------
        string : str
            The string to colorize.
        bold : bool
            Whether to bolden the string.

        Returns
        -------
        str
            The colorized string ready for terminal output.
        """
        return self.palette(self.code, string, background=self.background, bold=bold)


ColorBlack = Color(Palette8Bit(), 0)
"""
Black color on a 256 color palette preset.
"""

ColorWhite = Color(Palette8Bit(), 15)
"""
White color on a 256 color palette preset.
"""

ColorWhiteOnBlack = Color(Palette8Bit(), 15, background=0)
"""
White color on black blackground on a 256 color palette preset.
"""

ColorBlackOnWhite = Color(Palette8Bit(), 0, background=15)
"""
Black color on white background on a 256 color palette preset.
"""

ColorGold = Color(Palette8Bit(), 220)
"""
Gold color on a 256 color palette preset.
"""

ColorGreen = Color(Palette8Bit(), 40)
"""
Bright green color on a 256 color palette preset.
"""

ColorDarkGreen = Color(Palette8Bit(), 70)
"""
Dark green color on a 256 color palette preset.
"""

ColorMagenta = Color(Palette8Bit(), 165)
"""
Magenta color on a 256 color palette preset.
"""

ColorBlackOnGold = Color(Palette8Bit(), 0, background=220)
"""
Black color on gold background on a 256 color palette preset.
"""

ColorBlackOnOrange = Color(Palette8Bit(), 0, background=208)
"""
Black color on orange background on a 256 color palette preset.
"""

ColorBlackOnGray = Color(Palette8Bit(), 0, background=251)
"""
Black color on gray background on a 256 color palette preset.
"""
