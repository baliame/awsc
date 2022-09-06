"""
This module defines screen buffer classes for buffering output to the terminal.
"""


class Character:
    """
    Represents a single character cell on the screen. Each cell has a character value, a color, and a boldness flag.

    Attributes
    ----------
    value : str
        The character to display in the cell.
    color : awsc.termui.color.Color
        A callable which takes a string and returns a string. Designed with the Color object in mind, but can be replaced with any callable.
        Called when the cell is reset or changed to color the display character.
    bold : bool
        Whether the character should be displayed in bold.
    out : str
        The calculated output of the cell. Contains a control code to color the character, then the character, then a reset control code.
    dirty : bool
        Whether the character output needs recalculating.
    """

    def __init__(self):
        """
        Initializes a Character object.
        """
        self.value = " "
        self.color = Character.nullcolor
        self.bold = False
        self.out = " "
        self.dirty = False

    @staticmethod
    def nullcolor(x, **kwargs):
        """
        A null color object which does not add any control codes to the output.

        Parameters
        ----------
        x : str
            The character being colored.
        **kwargs : dict
            Contains the bold flag.

        Returns
        -------
        str
            The value of x, unchanged.
        """
        return x

    def clear(self):
        """
        Resets the character cell to a space character.
        """
        self.out = "\033[38;5;220m \033[0m"
        self.dirty = False

    def output(self):
        """
        Calculates the output of the character cell if required, and returns its output.

        Returns
        -------
        str
            The output of this character cell, which is the calculated value of the out attribute.
        """
        if self.dirty:
            self.dirty = False
            out = self.value
            if self.color is not None:
                out = self.color(out, bold=self.bold)
            self.out = out
        return self.out


class Screen:
    """
    Defines a screen. Unless some serious magic is being done with multiple terminal windows, this does not need to be instantiated more than
    once.

    Attributes
    ----------
    ui : awsc.termui.ui.UI
        The UI instance which controls this screen.
    buf : list(awsc.termui.screen.Screen.Row)
        A list of character rows on the screen.
    """

    def __init__(self, ui):
        """
        Initializes a Screen object.

        Parameters
        ----------
        ui : awsc.termui.ui.UI
            The UI instance which controls this screen.
        """
        self.ui = ui
        self.buf = []
        self.clear()

    class Row:
        """
        Defines a row of characters on the screen.

        Attributes
        ----------
        screen : awsc.termui.screen.Screen
            The Screen object which controls this row.
        buf : list(awsc.termui.screen.Character)
            A list of character cells in the row.
        """

        def __init__(self, screen):
            """
            Initializes a Row object.

            Parameters
            ----------
            screen : awsc.termui.screen.Screen
                The Screen instance which controls this row.
            """
            self.screen = screen
            self.buf = []
            self.clear()

        def clear(self):
            """
            Clears the row, resetting each character to an empty cell. If the dimensions of the screen changed, this also recreates the buffer
            with fresh empty characters matching the width of the row.
            """
            if len(self.buf) == self.screen.ui.width:
                for character in self.buf:
                    character.clear()
            else:
                self.buf = [Character() for i in range(self.screen.ui.width)]

        def __getitem__(self, i):
            """
            Returns the i-th cell in the row.

            Parameters
            ----------
            i : int
                The index of the cell within the row to retrieve.

            Returns
            -------
            awsc.termui.screen.Character
                The i-th cell in the row.
            """
            return self.buf[i]

        def output(self):
            """
            Returns the output of all cells in the row, as a single string.

            Returns
            -------
            str
                The output for the entire row.
            """
            return "".join(x.output() for x in self.buf)

    def clear(self):
        """
        Clears the screen, resetting each row to an empty row. If the dimensions of the screen changed, this also recreates the buffer
        with fresh empty row matching the height of the screen.
        """
        if len(self.buf) == self.ui.height:
            for row in self.buf:
                row.clear()
        else:
            self.buf = [Screen.Row(self) for i in range(self.ui.height)]

    def __getitem__(self, i):
        """
        Returns the i-th row on the screen.

        Parameters
        ----------
        i : int
            The index of the row to retrieve.

        Returns
        -------
        awsc.termui.screen.Screen.Row
            The i-th row on the screen..
        """
        return self.buf[i]

    def output(self):
        """
        Returns the output of all rows on the screen, as a single string.

        Returns
        -------
        str
            The output for the entire screen.
        """
        print("\r\n".join(x.output() for x in self.buf), end="")
