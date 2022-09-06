"""
This module defines base controls, which are interactive blocks.
"""
import threading
from typing import Any, Dict

from .block import Block
from .common import Commons


class BorderStyle:
    """
    Defines a border character set.

    Attributes
    ----------
    chars : list(str)
        A 6-element list which contains the border characters for the top/bottom, left/right sides, followed by the
        top left, top right, bottom left and bottom right corners.
    """

    def __init__(self, chars=None):
        """
        Initializes a BorderStyle object.

        Parameters
        ----------
        chars : list(str)
            A 6-element list which contains the border characters for the top/bottom, left/right sides, followed by the
            top left, top right, bottom left and bottom right corners.
        """
        if chars is None:
            chars = ["-", "|", "-", "-", "-", "-"]
        self.chars = chars[:]

    @property
    def horizontal(self):
        """
        Read-only property for the horizontal border character.

        Returns
        -------
        str
            The horizontal border character.
        """
        return self.chars[0]

    @property
    def vertical(self):
        """
        Read-only property for the vertical border character.

        Returns
        -------
        str
            The vertical border character.
        """
        return self.chars[1]

    @property
    def topleft(self):
        """
        Read-only property for the top left corner border character.

        Returns
        -------
        str
            The top left corner border character.
        """
        return self.chars[2]

    @property
    def topright(self):
        """
        Read-only property for the top right corner border character.

        Returns
        -------
        str
            The top right corner border character.
        """
        return self.chars[3]

    @property
    def bottomleft(self):
        """
        Read-only property for the bottom left corner border character.

        Returns
        -------
        str
            The bottom left corner border character.
        """
        return self.chars[4]

    @property
    def bottomright(self):
        """
        Read-only property for the bottom right corner border character.

        Returns
        -------
        str
            The bottom right corner border character.
        """
        return self.chars[5]


BorderStyleContinuous = BorderStyle(["─", "│", "┌", "┐", "└", "┘"])
"""
Border style preset with a set of characters that form a continuous border.
"""


class Border:
    """
    Defines the border of a control.

    Attributes
    ----------
    style : awsc.termui.control.BorderStyle
        The border style character set.
    color : awsc.termui.color.Color
        The color of the border.
    title : strs
        The main title to display in the title bar of the border.
    title_color : awsc.termui.color.Color
        The color of the main title text.
    title_info : str
        The additional information to display in the title bar of the border.
    title_info_color : awsc.termui.color.Color
        The color of the additional title info text.
    """

    def __init__(
        self,
        style=None,
        color=None,
        title=None,
        title_color=None,
        title_info=None,
        title_info_color=None,
    ):
        """
        Initializes a Border object.

        Parameters
        ----------
        style : awsc.termui.control.BorderStyle
            The border style character set.
        color : awsc.termui.color.Color
            The color of the border.
        title : str, optional
            The main title to display in the title bar of the border.
        title_color : awsc.termui.color.Color, optional
            The color of the main title text.
        title_info : str, optional
            The additional information to display in the title bar of the border.
        title_info_color : awsc.termui.color.Color, optional
            The color of the additional title info text.
        """
        self.style = style
        self.color = color
        self.title = title
        self.title_color = title_color
        self.title_info = title_info
        self.title_info_color = title_info_color

    def paint(self, block):
        """
        Paint hook for a border. Expected to output the border within the bounds of the parameter block.

        Parameters
        ----------
        block : awsc.termui.block.Block
            The block which this border is painted on.
        """
        if self.style is None or self.color is None:
            return
        corners = block.corners
        dimensions = block.dimensions()
        for i in range(corners[1][0], corners[1][1] + 1):
            if i == corners[1][0]:
                if self.title is None or self.title_color is None:
                    outer = (
                        self.style.topleft
                        + self.style.horizontal * (dimensions[0] - 1)
                        + self.style.topright
                    )
                    Commons.UIInstance.print(
                        outer, xy=(corners[0][0], i), color=self.color
                    )
                else:
                    total_title = self.title
                    if self.title_info is not None:
                        total_title = f"{self.title} ({self.title_info})"
                    cpos = int((dimensions[0] + 1) / 2)
                    spos = cpos - int(len(total_title) / 2) - 1
                    slen = len(total_title) + 2
                    outer = self.style.topleft + self.style.horizontal * spos
                    length = len(outer)
                    Commons.UIInstance.print(
                        outer, xy=(corners[0][0], i), color=self.color
                    )
                    outer = " " + self.title + " "
                    Commons.UIInstance.print(
                        outer,
                        xy=(corners[0][0] + length, i),
                        color=self.title_color,
                        bold=True,
                    )
                    length += len(outer)
                    if self.title_info is not None:
                        Commons.UIInstance.print(
                            "(",
                            xy=(corners[0][0] + length, i),
                            color=self.title_color,
                            bold=True,
                        )
                        length += 1
                        Commons.UIInstance.print(
                            self.title_info,
                            xy=(corners[0][0] + length, i),
                            color=self.title_color
                            if self.title_info_color is None
                            else self.title_info_color,
                            bold=True,
                        )
                        length += len(self.title_info)
                        Commons.UIInstance.print(
                            ") ",
                            xy=(corners[0][0] + length, i),
                            color=self.title_color,
                            bold=True,
                        )
                        length += 2
                    outer = (
                        self.style.horizontal * (dimensions[0] - 1 - spos - slen)
                        + self.style.topright
                    )
                    Commons.UIInstance.print(
                        outer, xy=(corners[0][0] + length, i), color=self.color
                    )
            elif i == corners[1][1]:
                outer = (
                    self.style.bottomleft
                    + self.style.horizontal * (dimensions[0] - 1)
                    + self.style.bottomright
                )
                Commons.UIInstance.print(outer, xy=(corners[0][0], i), color=self.color)
            else:
                outer = (
                    self.style.vertical
                    + " " * (dimensions[0] - 1)
                    + self.style.vertical
                )
                Commons.UIInstance.print(outer, xy=(corners[0][0], i), color=self.color)


BorderNone = Border()
"""
A preset which defines a border which paints nothing.
"""


class Control(Block):
    """
    The base object for all controllable blocks.

    Attributes
    ----------
    _border : awsc.termui.control.Border
        The border of the control.
    thread_share : dict
        A cross-thread storage for update threads to share data with the main execution thread.
    mutex : threading.Lock
        A mutex used to lock the cross-thread storage.
    """

    def __init__(self, *args, border=None, **kwargs):
        """
        Initializes a Control object.

        Parameters
        ----------
        border : awsc.termui.control.Border
            The border of the control.
        """
        super().__init__(*args, **kwargs)
        self.border = border
        self.thread_share = {}
        self.mutex = threading.Lock()

    @property
    def border(self):
        """
        Returns the border of the control.

        Returns
        -------
        awsc.termui.control.Border
            The border of the control.
        """
        return self._border

    @border.setter
    def border(self, value):
        """
        Sets the border of the control and forces a UI repaint.

        Parameters
        -------
        value : awsc.termui.control.Border
            The border of the control.
        """
        self._border = value
        Commons.UIInstance.dirty = True

    @property
    def inner(self):
        corners = self.corners
        x0 = corners[0][0] + (0 if self.border is None else 1)
        x1 = corners[0][1] - (0 if self.border is None else 1)
        y0 = corners[1][0] + (0 if self.border is None else 1)
        y1 = corners[1][1] - (0 if self.border is None else 1)
        return ((x0, x1), (y0, y1))

    @property
    def w_in(self):
        return self.width if self.border is None else self.width - 2

    def paint(self):
        if self.border is not None:
            self.border.paint(self)
        super().paint()


class HotkeyControl(Control):
    """
    Base class for all controls which implement a hotkey system.

    Attributes
    ----------
    hotkeys : dict
        A mapping of hotkeys to hotkey callbacks.
    tooltips : dict
        A mapping of hotkeys to short descriptions of their actions.
    hotkey_is_validated : dict
        A mapping of hotkey to bools. If a hotkey is validated, the validate_hotkey method will be called with the hotkey and it must
        return True for the hotkey to pass through to the input method.
    """

    class Autohotkey:
        """
        Decorator that automatically assigns a hotkey to a function upon instantiation.

        This is fuelled by the worst python can offer, I wish you the best of luck in understanding its source.

        Usage: @HotkeyControl.Autohotkey(key, tooltip=None, is_validated=False)

        HotkeyControl.Autohotkey may only be used for methods in classes which extend HotkeyControl.

        Attributes
        ----------
        key : str
            The hotkey to react to. See HotkeyControl.add_hotkey for more details.
        tooltip : str, optional
            Tooltip to associate with the hotkey. See HotkeyControl.add_hotkey for more details.
        is_validated : bool, default=False
            Is the hotkey validated? See HotkeyControl.add_hotkey for more details.
        condition : bool, default=False
            Run the condition callback of the HotkeyControl before adding.
        """

        _autohotkeys: Dict[str, Dict[str, Dict[str, Any]]] = {}

        def __init__(self, key, tooltip=None, is_validated=False, condition=False):
            self.key = key
            self.tooltip = None
            self.is_validated = is_validated

        def __call__(self, function):
            definer = function.__qualname__.split(".")[0]
            if definer not in self.__class__._autohotkeys:
                self.__class__._autohotkeys[definer] = {}
            self.__class__._autohotkeys[definer][self.key] = {
                "callback": function,
                "tooltip": self.tooltip,
                "is_validated": self.is_validated,
            }
            return function

        @classmethod
        def auto_hotkey(cls, self):
            """
            Performs automatically hotkeying up a HotkeyControl subclass.

            Inserts all inherited hotkeys automatically. Insertion is done in reverse of MRO - therefore, higher classes on the inheritance tree,
            such as HotkeyControl, insert their hotkeys first. This allows subclasses to overwrite these hotkeys.

            Parameters
            ----------
            self : awsc.termui.control.HotkeyControl
                The class being initialized.
            """
            import inspect

            for classobj in reversed(inspect.getmro(self.__class__)):
                classname = classobj.__name__
                if classname in cls._autohotkeys:
                    for hotkey, definition in cls._autohotkeys[classname].items():
                        # pylint: disable=unnecessary-dunder-call # Offering a bounty of a single point of reddit karma if anyone can tell me why.
                        self.add_hotkey(
                            hotkey,
                            definition["callback"].__get__(self, self.__class__),
                            definition["tooltip"],
                            definition["is_validated"],
                        )

    def __init__(self, *args, **kwargs):
        """
        Initializes a HotkeyControl object.
        """
        super().__init__(*args, **kwargs)
        self.hotkeys = {}
        self.tooltips = {}
        self.hotkey_is_validated = {}
        HotkeyControl.Autohotkey.auto_hotkey(self)

    def autohotkey_condition(self, hotkey):
        """
        Autohotkey condition callback. Called with the key name if the key is conditional.

        Parameters
        ----------
        hotkey : str
            The key definition.

        Returns
        -------
        bool
            True if condition is met.
        """
        return True

    def add_hotkey(self, hotkey, action, tooltip=None, is_validated=False):
        """
        Adds a new hotkey to the control.

        Parameters
        ----------
        hotkey : str
            The hotkey for the action being added. Hotkeys can be a number of things:
            * A character, such as 'a' or '.', directly equivalent to pressing the associated key. Not case sensitive.
            * A control code from awsc.termui.ui.ControlCodes. Control codes are the equivalent of holding the CTRL key while pressing the hotkey,
              so ControlCodes.A is CTRL+A. Note that due to how the terminal handles control codes (^A being 0, ^B being 1, and so on), certain
              control codes such as CTRL+J are unavailable, as their codes are equivalent to the codes of keys that type special characters, such
              as ENTER or TAB.
            * A key name. Special keys may be referred to by name, such as KEY_ESCAPE or KEY_ENTER. A list of key names is available in the
              documentation of the blessed library (https://blessed.readthedocs.io/en/latest/keyboard.html).
        action : callable(object)
            The callback to call if the hotkey is pressed and optionally passes validation. The callback is passed a single parameter, which is
            this object and does not need to return a value.
        tooltip : str, optional
            An optional tooltip associated with the hotkey. This may be used by other controls to create hotkey displays.
        is_validated: bool, default=False
            If True, hotkey must pass validation before being handled. Validation is implemented by the control in the validate_hotkey method.
        """
        self.hotkeys[hotkey] = action
        if tooltip is not None:
            self.tooltips[hotkey] = tooltip
        self.hotkey_is_validated[hotkey] = is_validated
        Commons.UIInstance.dirty = True

    def validate_hotkey(self, key):
        """
        Validates whether a hotkey can be used based on the state of the control.

        Parameters
        ----------
        key : str
            The hotkey being used, which is either a lowercase character, a control code or a key name based on which key was pressed.

        Returns
        -------
        bool
            Returns True if the hotkey is usable, False to prevent using it.
        """
        return True

    def input(self, key):
        inkey = str(key)
        if key.is_sequence:
            inkey = key.name
        else:
            inkey = inkey.lower()
        if inkey in self.hotkeys:
            if not self.hotkey_is_validated[inkey] or self.validate_hotkey(inkey):
                self.hotkeys[inkey](self)
                Commons.UIInstance.dirty = True
            return True
        return False
