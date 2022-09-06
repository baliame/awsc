"""
This module defines dialogs, which are modal controls designed to be displayed as topmost blocks for inputting data.
"""
from .color import ColorBlackOnGold, ColorBlackOnOrange, ColorGold
from .common import Commons
from .control import Control


class DialogField:
    """
    Base class for input fields on a dialog.

    Attributes
    ----------
    highlightable : bool
        Whether the field can be selected. Unhighlightable fields are useful for labels.
    centered : bool
        Whether to forcibly center the field within the dialog.
    """

    def __init__(self):
        self.highlightable = False
        self.centered = False
        Commons.UIInstance.dirty = True

    def input(self, inkey):
        """
        Input handler method for the field. Works identically to the input method of a block.

        Parameters
        ----------
        inkey : blessed.keyboard.Keystroke
            The key that was pressed.

        Returns
        -------
        bool
            Whether the input was handled.
        """
        return False

    def paint(self, x0, x1, y, selected=False):
        """
        Paint callback for the field. Responsible for outputting the entire field.

        Parameters
        ----------
        x0 : int
            The left bound of the field, as determined by the parent dialog.
        x1 : int
            The right bound of the field, as determined by the parent dialog.
        y : int
            The y of the field, as determined by the parent dialog.
        selected : bool, default=False
            Whether the field is currently selected.
        """

    @property
    def value(self):
        """
        Read-only property for retrieving a generalized value of the field.
        """
        return None


class DialogFieldLabel(DialogField):
    """
    A field which displays a static text. Cannot be selected.

    Attributes
    ----------
    default_color : awsc.termui.color.Color
        The default color for the text of this label.
    texts : list(tuple(str, awsc.termui.color.Color))
        A list of text snippets, each associated with a color to draw it with. Text snippets are printed sequentially.
        If any list entry is a str instead of a tuple, it will be printed with the default color. This is done for the sake of both legacy
        and simplicity.
    """

    def __init__(self, texts, default_color=ColorGold, centered=True):
        super().__init__()
        self.default_color = default_color
        if isinstance(texts, str):
            self.texts = [(texts, default_color)]
        else:
            self.texts = list(texts[:])
        self.centered = centered

    @property
    def value(self):
        return self.text

    @property
    def text(self):
        """
        Property. Returns the raw text displayed by the label as a string. When set, replaces the entire text of the field with
        the provided text and default color.
        """
        return "".join([a[0] for a in self.texts])

    @text.setter
    def text(self, value):
        if isinstance(value, list):
            self.texts = value
        else:
            self.texts = [(value, self.default_color)]

    def add_text(self, text, color=None):
        """
        Adds a new text snippet to the label, optionally with a set color.

        Parameters
        ----------
        text : str
            The text snippet to add.
        color : awsc.termui.color.Color, optional
            The color of the text. Default color attribute is used if omitted.
        """
        if color is None:
            color = self.default_color
        self.texts.append((text, color))

    def paint(self, x0, x1, y, selected=False):
        x = x0
        if self.centered:
            textlen = 0
            for text in self.texts:
                textlen += len(text[0])
            width = x1 - x0 + 1
            x = int(width / 2) - int(textlen / 2) + x0 + 1
        for text in self.texts:
            Commons.UIInstance.print(text[0], xy=(x, y), color=text[1])
            x += len(text[0])


class DialogFieldButton(DialogField):
    """
    A button on the dialog. While selected, hitting the enter key will execute the button's callback function.

    Attributes
    ----------
    text : str
        The text to display on the button.
    color : awsc.termui.color.Color
        The color of the button when not selected.
    selected_color : awsc.termui.color.Color
        The color of the button when selected.
    action : callable
        The callback to call when the button is pressed. No parameters are passed to the callback.
    """

    def __init__(self, text, action, color=ColorGold, selected_color=ColorBlackOnGold):
        super().__init__()
        self.highlightable = True
        self.text = text
        self.color = color
        self.selected_color = selected_color
        self.centered = True
        self.action = action

    @property
    def value(self):
        return self.text

    def input(self, inkey):
        if inkey.is_sequence and inkey.name == "KEY_ENTER":
            self.action()
            Commons.UIInstance.dirty = True
        return True

    def paint(self, x0, x1, y, selected=False):
        x = x0
        if self.centered:
            textlen = len(self.text) + 4
            width = x1 - x0 + 1
            x = int(width / 2) - int(textlen / 2) + x0
        Commons.UIInstance.print(
            f"< {self.text} >",
            xy=(x, y),
            color=self.selected_color if selected else self.color,
        )


class DialogFieldCheckbox(DialogField):
    """
    A checkbox toggle on the dialog. While selected, hitting the enter key will toggle the checked state of the checkbox.

    Attributes
    ----------
    label : str
        The text to display next to the checkbox.
    color : awsc.termui.color.Color
        The color of the checkbox when not selected.
    selected_color : awsc.termui.color.Color
        The color of the checkbox when selected.
    checked : bool
        Whether the checkbox is checked.
    char_unchecked : str
        The checkbox display character for when it is not checked.
    char_checked : str
        The checkbox display character for when it is checked.
    """

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

    @property
    def value(self):
        return self.checked

    def input(self, inkey):
        if inkey.is_sequence and inkey.name == "KEY_ENTER":
            self.checked = not self.checked
            Commons.UIInstance.dirty = True
        return True

    def paint(self, x0, x1, y, selected=False):
        x = x0
        checkbox_character = self.char_checked if self.checked else self.char_unchecked
        text = f"{checkbox_character} {self.label}"
        if self.centered:
            textlen = len(text)
            width = x1 - x0 + 1
            x = int(width / 2) - int(textlen / 2) + x0
        Commons.UIInstance.print(
            text, xy=(x, y), color=self.selected_color if selected else self.color
        )


class DialogFieldText(DialogField):
    """
    An input textfield on the dialog.

    Attributes
    ----------
    label : str
        The text to display next to the input field.
    text : str
        The text that is currently typed into the input field.
    color : awsc.termui.color.Color
        The color of the textfield when not selected.
    selected_color : awsc.termui.color.Color
        The color of the textfield when selected.
    label_color : awsc.termui.color.Color
        The color of the label of the textfield.
    label_min : int
        The minimum width that must be allocated for the label.
    password : bool
        If set, masks the text of the textfield with asterisks.
    drawable : int
        The calculated width of the interactive part of the textfield.
    left : int
        How much the textfield is scrolled to the right, in characters.
    accepted_inputs : str
        A string of characters which are acceptable inputs in the textfield. No character not present in the string will be typeable into
        the textfield.
    """

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

    @property
    def value(self):
        return self.text

    def input(self, inkey):
        if inkey.is_sequence:
            if inkey.name == "KEY_LEFT":
                if self.left > 0:
                    self.left -= 1
                Commons.UIInstance.dirty = True
                return True
            if inkey.name == "KEY_RIGHT":
                self.left += 1
                Commons.UIInstance.dirty = True
                return True
            if inkey.name == "KEY_HOME":
                self.left = 0
                Commons.UIInstance.dirty = True
                return True
            if inkey.name == "KEY_END":
                self.left = max(len(self.text) - self.drawable, 0)
                Commons.UIInstance.dirty = True
                return True
            if inkey.name == "KEY_BACKSPACE" and len(self.text) > 0:
                self.text = self.text[:-1]
                Commons.UIInstance.dirty = True
                return True
            if inkey.name == "KEY_DELETE":
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
    """
    A generic dialog. A dialog is intended to be used as a form that can be filled by the user for some action to happen.

    Attributes
    ----------
    highlighted : int
        The index of the control that is currently selected.
    fields : list(awsc.termui.dialog.DialogField)
        A list of field objects associated with the dialog.
    bookmark : int
        The position where the next field will be inserted. The confirm and cancel buttons, if used, are forcibly pushed as the last controls
        in the list, so bookmark always preceeds the confirm and cancel buttons.
    background_color : awsc.termui.color.Color
        The background color to fill the dialog with.
    """

    def __init__(
        self,
        *args,
        ok_action=None,
        cancel_action=None,
        background_color=None,
        confirm_text="Ok",
        cancel_text="Cancel",
        color=ColorGold,
        selected_color=ColorBlackOnGold,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
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
        """
        A callable that does nothing, for the purpose of having such a callable.
        """

    def add_field(self, field):
        """
        Inserts a new field into the dialog. This will be inserted as the last field before the confirm and cancel buttons.

        Parameters
        ----------
        field : awsc.termui.dialog.DialogField
            The field to insert.
        """
        self.fields.insert(self.bookmark, field)
        self.bookmark += 1
        for i, elem in enumerate(self.fields):
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
        if key.is_sequence and key.name == "KEY_BTAB":
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
        corners = self.corners
        if self.background_color is not None:
            width = corners[0][1] - corners[0][0] + 1
            for row in range(corners[1][0], corners[1][1] + 1):
                Commons.UIInstance.print(
                    " " * width, xy=(corners[0][0], row), color=self.background_color
                )
        super().paint()
        buttons = []
        indices = {}
        y = corners[1][0] + (1 if self.border is None else 2)
        x0 = corners[0][0] + (1 if self.border is None else 2)
        x1 = corners[0][1] - (1 if self.border is None else 2)
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
        y = corners[1][1] - (1 if self.border is None else 2)
        if len(buttons) > 0:
            subdiv = float((x1 - x0 + 1) / len(buttons))
            width = int(subdiv)
            rem = subdiv - width
            remacc = 0
            for button in buttons:
                remacc += rem
                x1 = x0 + width
                if remacc > 0.5:
                    x1 += 1
                    remacc -= 1
                button.paint(x0, x1, y, indices[button] == self.highlighted)
                x0 = x1 + 1
