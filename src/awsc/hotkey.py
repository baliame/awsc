"""
Module for hotkey display.
"""

from .common import Common
from .termui.alignment import Dimension, TopRightAnchor
from .termui.common import column_sizer
from .termui.control import Control
from .termui.ui import ControlCodes


class HotkeyDisplay(Control):
    """
    The hotkey display is the display element in the top right, listing valid hotkeys accepted by the current controls on screen. Each element will provider its
    own hotkey display instance, filled with its own and the global hotkeys.

    Attributes
    ----------
    translations : dict
        A mapping of key names to their nicely presentable forms.
    holder : awsc.termui.control.HotkeyControl
        The control whose hotkeys this displays.
    cols : int
        The number of info columns to divide the available space to.
    highlight_color : awsc.termui.color.Color
        The color of the keys on the hotkey display.
    generic_color : awsc.termui.color.Color
        The color of the tooltips on the hotkey display.
    session : awsc.session.Session
        A reference to the session object.
    """

    @classmethod
    def opener(cls, *args, caller, **kwargs):
        """
        Simplified initializer for a hotkey display, following the patterns defined by other controls.
        """

        return cls(
            caller.parent,
            TopRightAnchor(1, 0),
            Dimension("33%|50", 8),
            holder=caller,
            session=Common.Session,
            highlight_color=Common.color("hotkey_display_title"),
            generic_color=Common.color("hotkey_display_value"),
        )

    translations = {
        "KEY_DOWN": "↓",
        "KEY_RIGHT": "→",
        "KEY_UP": "↑",
        "KEY_LEFT": "←",
        "KEY_ENTER": "↲",
        "\n": "↲",
        "\t": "↹",
        "KEY_BACKSPACE": "⇦",
        "KEY_DELETE": "del",
        "KEY_END": "end",
        "KEY_HOME": "home",
        "KEY_ESCAPE": "esc",
        "KEY_PGUP": "pgup",
        "KEY_PGDOWN": "pgdn",
        "KEY_INSERT": "ins",
        ControlCodes.A: "ctrl-a",
        ControlCodes.B: "ctrl-b",
        ControlCodes.C: "ctrl-c",
        ControlCodes.D: "ctrl-d",
        ControlCodes.E: "ctrl-e",
        ControlCodes.F: "ctrl-f",
        ControlCodes.G: "ctrl-g",
        ControlCodes.K: "ctrl-k",
        ControlCodes.L: "ctrl-l",
        ControlCodes.M: "ctrl-m",
        ControlCodes.N: "ctrl-n",
        ControlCodes.O: "ctrl-o",
        ControlCodes.P: "ctrl-p",
        ControlCodes.Q: "ctrl-q",
        ControlCodes.R: "ctrl-r",
        ControlCodes.S: "ctrl-s",
        ControlCodes.T: "ctrl-t",
        ControlCodes.U: "ctrl-u",
        ControlCodes.V: "ctrl-v",
        ControlCodes.W: "ctrl-w",
        ControlCodes.X: "ctrl-x",
        ControlCodes.Y: "ctrl-y",
        ControlCodes.Z: "ctrl-z",
    }

    def __init__(
        self,
        *args,
        holder,
        session=None,
        cols=2,
        highlight_color=None,
        generic_color=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.holder = holder
        self.cols = cols
        self.highlight_color = highlight_color
        self.generic_color = generic_color
        self.session = session

    def paint(self):
        super().paint()
        ((x0, x1), (y0, y1)) = self.inner
        width = x1 - x0 + 1
        colw = int(width / self.cols)
        x = x0
        y = y0
        col = 0
        longest = []
        tooltips = {**self.holder.tooltips, **self.session.global_hotkey_tooltips}
        labels = []
        generated = {}
        for hotkey, tooltip in tooltips.items():
            display = (
                "<"
                + (
                    HotkeyDisplay.translations[hotkey]
                    if hotkey in HotkeyDisplay.translations
                    else hotkey
                )
                + "> "
            )
            labels.append(display)
            generated[hotkey] = display
        longest = column_sizer(y0, y1, labels, None)
        for hotkey, tooltip in tooltips.items():
            display = generated[hotkey]
            if len(display) < longest[col]:
                display += " " * (longest[col] - len(display))
            Common.Session.ui.print(
                display, xy=(x, y), color=self.highlight_color, bold=True
            )
            text = tooltip if not callable(tooltip) else tooltip()

            if len(text) > colw - longest[col]:
                text = text[: colw - longest[col]]
            Common.Session.ui.print(
                text, xy=(x + longest[col], y), color=self.generic_color
            )
            y += 1
            if y > y1:
                (x, y, col) = (x + colw, y0, col + 1)
