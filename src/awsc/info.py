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
        info=[],
        cols=2,
        highlight_color=None,
        generic_color=None,
        *args,
        **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        self.info = {}
        self.order = info[:]
        self.special_colors = {}
        for k in info:
            self.info[k] = None
        self.cols = cols
        self.highlight_color = highlight_color
        self.generic_color = generic_color
        self.commander_hook = None
        self.filterer_hook = None

    def input(self, inkey):
        if inkey == ":" and self.commander_hook is not None:
            self.commander_hook()
            return True
        if inkey == "/" and self.filterer_hook is not None:
            self.filterer_hook()
            return True
        return False

    def __getitem__(self, k):
        return self.info[k] if k in self.info else None

    def __setitem__(self, k, v):
        if k not in self.order:
            self.order.append(k)
        self.info[k] = v

    def paint(self):
        super().paint()
        (x0, x1), (y0, y1) = self.inner
        w = x1 - x0 + 1
        colw = int(w / self.cols)
        x = x0
        y = y0
        longest = []
        v = 0

        for name in self.order:
            if name not in self.info:
                continue
            display = name + ": "
            if len(display) > v:
                v = len(display)
            y += 1
            if y > y1:
                y = y0
                longest.append(v)
                v = 0
        if v > 0:
            longest.append(v)
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
            t = value
            if len(t) > colw - longest[col]:
                t = t[: colw - longest[col]]
            Commons.UIInstance.print(
                t,
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
    def input(self, inkey):
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
        session=None,
        cols=2,
        highlight_color=None,
        generic_color=None,
        *args,
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
        c = self.corners()
        x0 = c[0][0] + (0 if self.border is None else 1)
        x1 = c[0][1] - (0 if self.border is None else 1)
        y0 = c[1][0] + (0 if self.border is None else 1)
        y1 = c[1][1] - (0 if self.border is None else 1)
        w = x1 - x0 + 1
        colw = int(w / self.cols)
        x = x0
        y = y0
        longest = []
        v = 0
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
            if len(display) > v:
                v = len(display)
            y += 1
            if y > y1:
                y = y0
                longest.append(v)
                v = 0
        if v > 0:
            longest.append(v)
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
            t = tooltip if not callable(tooltip) else tooltip()
            if len(t) > colw - longest[col]:
                t = t[: colw - longest[col]]
            Commons.UIInstance.print(
                t, xy=(x + longest[col], y), color=self.generic_color
            )
            y += 1
            if y > y1:
                y = y0
                col += 1
                x += colw
