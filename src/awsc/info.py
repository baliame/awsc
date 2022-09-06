"""
Module for informational display controls.
"""
from typing import Callable

from .termui.common import Commons, column_sizer
from .termui.control import Control
from .termui.dialog import DialogControl


class InfoDisplay(Control):
    """
    The info display is the control situated in the top left corner of the screen. It is intended to display information on the active session as a list
    of key-value pairs. The info display also registers the global hotkeys.

    Attributes
    ----------
    info : dict
        The actual info being displayed, as a mapping of label to data.
    order : list
        The order in which the info should be displayed.
    special_colors : dict
        A mapping of label to color for which pieces of data should be highlighted with a non-standard color, for example, for use with errors.
    cols : int
        The number of info columns to divide the available space to.
    highlight_color : awsc.termui.color.Color
        The color of the label.
    generic_color : awsc.termui.color.Color
        The default color of data.
    commander_hook : callable
        The callback to call for opening the commander.
    filterer_hook : callable
        The callback to call for opening the filterer.
    """

    def __init__(
        self,
        *args,
        info=None,
        cols=2,
        highlight_color=None,
        generic_color=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.info = {}
        self.order = info[:] if info is not None else []
        self.special_colors = {}
        for k in info:
            self.info[k] = None
        self.cols = cols
        self.highlight_color = highlight_color
        self.generic_color = generic_color
        self.commander_hook: Callable[[], None] = None
        self.filterer_hook: Callable[[], None] = None

    def input(self, key):
        if key == ":" and self.commander_hook is not None:
            # pylint: disable=not-callable # Member is callable or None, and check asserts that it is not None
            self.commander_hook()
            return True
        if key == "/" and self.filterer_hook is not None:
            # pylint: disable=not-callable # Member is callable or None, and check asserts that it is not None
            self.filterer_hook()
            return True
        return False

    def __getitem__(self, key):
        return self.info[key] if key in self.info else None

    def __setitem__(self, key, value):
        if key not in self.order:
            self.order.append(key)
        self.info[key] = value

    def paint(self):
        super().paint()
        (x0, x1), (y0, y1) = self.inner
        width = x1 - x0 + 1
        colw = int(width / self.cols)
        x = x0
        y = y0
        longest = column_sizer(y0, y1, self.order, self.info)
        col = 0

        for name in self.order:
            if name not in self.info:
                continue
            value = self.info[name]
            if value is None:
                value = ""
            display = name + ": "
            if len(display) < longest[col]:
                display += " " * (longest[col] - len(display))
            Commons.UIInstance.print(
                display, xy=(x, y), color=self.highlight_color, bold=True
            )
            text = value
            if len(text) > colw - longest[col]:
                text = text[: colw - longest[col]]
            Commons.UIInstance.print(
                text,
                xy=(x + longest[col], y),
                color=self.generic_color
                if name not in self.special_colors
                else self.special_colors[name],
            )
            y += 1
            if y > y1:
                (x, y, col) = (x + colw, y0, col + 1)


class NeutralDialog(DialogControl):
    """
    A dialog that does nothing and handles no inputs.
    """

    def input(self, key):
        return False
