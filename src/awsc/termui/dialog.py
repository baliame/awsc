from .color import ColorBlackOnGold, ColorBlackOnOrange, ColorGold
from .common import Commons
from .control import Control


class DialogField:
    def __init__(self):
        self.highlightable = False
        self.centered = False
        Commons.UIInstance.dirty = True

    def input(self, inkey):
        return False

    def paint(self, x0, x1, y, selected=False):
        pass


class DialogFieldLabel(DialogField):
    def __init__(self, texts, default_color=ColorGold, centered=True):
        super().__init__()
        self.default_color = default_color
        if isinstance(texts, str):
            self.texts = [(texts, default_color)]
        else:
            self.texts = list(texts[:])
        self.centered = centered

    @property
    def text(self):
        return "".join([a[0] for a in self.texts])

    @text.setter
    def text(self, value):
        self.texts = [(value, self.default_color)]

    def add_text(self, text, color=None):
        if color is None:
            color = self.default_color
        self.texts.append((text, color))

    def paint(self, x0, x1, y, selected=False):
        x = x0
        if self.centered:
            textlen = 0
            for t in self.texts:
                textlen += len(t[0])
            w = x1 - x0 + 1
            x = int(w / 2) - int(textlen / 2) + x0 + 1
        for t in self.texts:
            Commons.UIInstance.print(t[0], xy=(x, y), color=t[1])
            x += len(t[0])


class DialogFieldButton(DialogField):
    def __init__(self, text, action, color=ColorGold, selected_color=ColorBlackOnGold):
        super().__init__()
        self.highlightable = True
        self.text = text
        self.color = color
        self.selected_color = selected_color
        self.centered = True
        self.action = action

    def input(self, inkey):
        if inkey.is_sequence and inkey.name == "KEY_ENTER":
            self.action()
            Commons.UIInstance.dirty = True
        return True

    def paint(self, x0, x1, y, selected=False):
        x = x0
        if self.centered:
            textlen = len(self.text) + 4
            w = x1 - x0 + 1
            x = int(w / 2) - int(textlen / 2) + x0
        Commons.UIInstance.print(
            "< {0} >".format(self.text),
            xy=(x, y),
            color=self.selected_color if selected else self.color,
        )


class DialogFieldCheckbox(DialogField):
    def __init__(
        self, label, checked=False, color=ColorGold, selected_color=ColorBlackOnGold
    ):
        super().__init__()
        self.highlightable = True
        self.checked = checked
        self.label = label
        self.color = color
        self.selected_color = selected_color
        self.char_unchecked = "☐"
        self.char_checked = "☑"

    def input(self, inkey):
        if inkey.is_sequence and inkey.name == "KEY_ENTER":
            self.checked = not self.checked
            Commons.UIInstance.dirty = True
        return True

    def paint(self, x0, x1, y, selected=False):
        x = x0
        text = "{0} {1}".format(
            self.char_checked if self.checked else self.char_unchecked, self.label
        )
        if self.centered:
            textlen = len(text)
            w = x1 - x0 + 1
            x = int(w / 2) - int(textlen / 2) + x0
        Commons.UIInstance.print(
            text, xy=(x, y), color=self.selected_color if selected else self.color
        )


class DialogFieldText(DialogField):
    def __init__(
        self,
        label,
        text="",
        color=ColorBlackOnOrange,
        selected_color=ColorBlackOnGold,
        label_color=ColorGold,
        label_min=0,
        password=False,
        accepted_inputs=None,
    ):
        super().__init__()
        self.highlightable = True
        self.left = 0
        self.text = text
        self.label = label
        self.color = color
        self.label_color = label_color
        self.label_min = label_min
        self.selected_color = selected_color
        self.centered = True
        self.password = password
        self.drawable = 0
        if accepted_inputs is None:
            self.accepted_inputs = Commons.TextfieldInputs
        else:
            self.accepted_inputs = accepted_inputs

    def input(self, inkey):
        if inkey.is_sequence:
            if inkey.name == "KEY_LEFT":
                if self.left > 0:
                    self.left -= 1
                Commons.UIInstance.dirty = True
                return True
            elif inkey.name == "KEY_RIGHT":
                self.left += 1
                Commons.UIInstance.dirty = True
                return True
            elif inkey.name == "KEY_HOME":
                self.left = 0
                Commons.UIInstance.dirty = True
                return True
            elif inkey.name == "KEY_END":
                self.left = len(self.text) - self.drawable
                if self.left < 0:
                    self.left = 0
                Commons.UIInstance.dirty = True
                return True
            elif inkey.name == "KEY_BACKSPACE" and len(self.text) > 0:
                self.text = self.text[:-1]
                Commons.UIInstance.dirty = True
                return True
            elif inkey.name == "KEY_DELETE":
                self.text = ""
                Commons.UIInstance.dirty = True
                return True
        elif inkey in self.accepted_inputs:
            self.text += inkey
            if len(self.text) > self.drawable:
                self.left = len(self.text) - self.drawable + 1
            Commons.UIInstance.dirty = True
            return True
        return False

    def paint(self, x0, x1, y, selected=False):
        x = x0
        Commons.UIInstance.print(self.label, xy=(x, y), color=self.label_color)
        x += max(len(self.label) + 1, self.label_min)
        space = x1 - x + 1
        self.drawable = space
        if self.left >= len(self.text):
            self.left = 0
        text = self.text[
            self.left : (
                self.left + space
                if len(self.text) > self.left + space
                else len(self.text)
            )
        ]
        if self.password:
            text = "*" * len(text)
        if len(text) < space:
            text += " " * (space - len(text))
        Commons.UIInstance.print(
            text, xy=(x, y), color=self.selected_color if selected else self.color
        )


class DialogControl(Control):
    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        ok_action=None,
        cancel_action=None,
        background_color=None,
        confirm_text="Ok",
        cancel_text="Cancel",
        color=ColorGold,
        selected_color=ColorBlackOnGold,
        **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        self.highlighted = 0
        self.bookmark = 0
        self.background_color = background_color

        self.fields = []
        if confirm_text is not None:
            self.fields.append(
                DialogFieldButton(
                    confirm_text,
                    ok_action if ok_action is not None else self.nop,
                    color,
                    selected_color,
                )
            )
        if cancel_text is not None:
            self.fields.append(
                DialogFieldButton(
                    cancel_text,
                    cancel_action if cancel_action is not None else self.nop,
                    color,
                    selected_color,
                )
            )

    def nop(self):
        Commons.UIInstance.log("WARN: DialogControl NOP action executed.")

    def add_field(self, field):
        self.fields.insert(self.bookmark, field)
        self.bookmark += 1
        for i in range(len(self.fields)):
            elem = self.fields[i]
            if elem.highlightable:
                self.highlighted = i
                break

    def input(self, key):
        if key == "\t":
            orig = self.highlighted
            while True:
                self.highlighted += 1
                if self.highlighted >= len(self.fields):
                    self.highlighted -= len(self.fields)
                if self.fields[self.highlighted].highlightable:
                    break
                if self.highlighted == orig:
                    break
            Commons.UIInstance.dirty = True
            return True
        elif key.is_sequence and key.name == "KEY_BTAB":
            orig = self.highlighted
            while True:
                self.highlighted -= 1
                if self.highlighted < 0:
                    self.highlighted += len(self.fields)
                if self.fields[self.highlighted].highlightable:
                    break
                if self.highlighted == orig:
                    break
            Commons.UIInstance.dirty = True
            return True
        self.fields[self.highlighted].input(key)
        return True  # Modals should prevent input from being piped to others.

    def paint(self):
        c = self.corners()
        if self.background_color is not None:
            w = c[0][1] - c[0][0] + 1
            for row in range(c[1][0], c[1][1] + 1):
                Commons.UIInstance.print(
                    " " * w, xy=(c[0][0], row), color=self.background_color
                )
        super().paint()
        buttons = []
        indices = {}
        y = c[1][0] + (1 if self.border is None else 2)
        x0 = c[0][0] + (1 if self.border is None else 2)
        x1 = c[0][1] - (1 if self.border is None else 2)
        # Commons.UIInstance.log('Paint dialog: x0={0}, x1={1}'.format(x0, x1))
        idx = 0
        for item in self.fields:
            if isinstance(item, DialogFieldButton):
                buttons.append(item)
                indices[item] = idx
            else:
                item.paint(x0, x1, y, idx == self.highlighted)
                y += 1
            idx += 1
        y = c[1][1] - (1 if self.border is None else 2)
        if len(buttons) > 0:
            subdiv = float((x1 - x0 + 1) / len(buttons))
            w = int(subdiv)
            rem = subdiv - w
            remacc = 0
            for button in buttons:
                remacc += rem
                x1 = x0 + w
                if remacc > 0.5:
                    x1 += 1
                    remacc -= 1
                button.paint(x0, x1, y, indices[button] == self.highlighted)
                x0 = x1 + 1
