from typing import Callable

from .termui.common import Commons
from .termui.control import Control
from .termui.dialog import DialogControl
from .termui.ui import ControlCodes


class InfoDisplay(Control):
    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        info=None,
        cols=2,
        highlight_color=None,
        generic_color=None,
        **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
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
        longest = []
        length = 0

        for name in self.order:
            if name not in self.info:
                continue
            display = name + ": "
            if len(display) > length:
                length = len(display)
            y += 1
            if y > y1:
                y = y0
                longest.append(length)
                length = 0
        if length > 0:
            longest.append(length)
        y = y0
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
                y = y0
                col += 1
                x += colw


class NeutralDialog(DialogControl):
    def input(self, key):
        return False


class HotkeyDisplay(Control):
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
        parent,
        alignment,
        dimensions,
        holder,
        *args,
        session=None,
        cols=2,
        highlight_color=None,
        generic_color=None,
        **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        self.holder = holder
        self.cols = cols
        self.highlight_color = highlight_color
        self.generic_color = generic_color
        self.session = session

    def paint(self):
        super().paint()
        corners = self.corners()
        x0 = corners[0][0] + (0 if self.border is None else 1)
        x1 = corners[0][1] - (0 if self.border is None else 1)
        y0 = corners[1][0] + (0 if self.border is None else 1)
        y1 = corners[1][1] - (0 if self.border is None else 1)
        width = x1 - x0 + 1
        colw = int(width / self.cols)
        x = x0
        y = y0
        longest = []
        length = 0
        tooltips = {**self.holder.tooltips, **self.session.global_hotkey_tooltips}
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
            if len(display) > length:
                length = len(display)
            y += 1
            if y > y1:
                y = y0
                longest.append(length)
                length = 0
        if length > 0:
            longest.append(length)
        y = y0
        col = 0
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
            if len(display) < longest[col]:
                display += " " * (longest[col] - len(display))
            Commons.UIInstance.print(
                display, xy=(x, y), color=self.highlight_color, bold=True
            )
            text = tooltip if not callable(tooltip) else tooltip()
            if len(text) > colw - longest[col]:
                text = text[: colw - longest[col]]
            Commons.UIInstance.print(
                text, xy=(x + longest[col], y), color=self.generic_color
            )
            y += 1
            if y > y1:
                y = y0
                col += 1
                x += colw
