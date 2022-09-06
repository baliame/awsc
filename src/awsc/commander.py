"""
Module that contains the special control bars for the awsc UI.
"""
from .termui.common import Commons
from .termui.control import Control


class Filterer(Control):
    """
    The Filterer is the command bar for filtering the currently active control. Different top level controls react differently to filtering.
    Lister controls will hide elements not matching the filter. Text browser controls will highlight matches in their text and jump between
    matches.

    Attributes
    ----------
    session : awsc.session.Session
        The session manager object.
    color : awsc.termui.color.Color
        The color of the control's text and borders.
    symbol_color : awsc.termui.color.Color
        The color of the symbol for the filter bar.
    inactive_color : awsc.termui.color.Color
        The color of the bar when it is inactive.
    paused : bool
        Whether the bar is inactive. The inactive bar still applies its filter, but pressing keys does not type into it.
    accepted_input : str
        The list of accepted input keys. Defaults to accepted textfield inputs.
    text : str
        The current filter.
    """

    def __init__(self, *args, session, color, symbol_color, inactive_color, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        self.color = color
        self.symbol_color = symbol_color
        self.inactive_color = inactive_color
        self.paused = False
        self.session.filterer = self
        self.accepted_input = Commons.TextfieldInputs
        self.text = ""

    def input(self, key):
        if self.paused and not (key.is_sequence and key.name == "KEY_ESCAPE"):
            return False
        if key.is_sequence:
            if key.name == "KEY_ENTER":
                self.pause()
            elif key.name == "KEY_ESCAPE":
                self.session.resource_main.filter = None
                self.close()
            elif key.name == "KEY_BACKSPACE":
                if len(self.text) > 0:
                    self.text = self.text[:-1]
                self.session.resource_main.filter = self.text
            elif key.name == "KEY_DELETE":
                self.text = ""
                self.session.resource_main.filter = self.text
            Commons.UIInstance.dirty = True
        elif str(key) in self.accepted_input:
            self.text += key
            self.session.resource_main.filter = self.text
            Commons.UIInstance.dirty = True
        return True

    def pause(self):
        """
        Sets pause flag.
        """
        self.paused = True

    def resume(self):
        """
        Unsets pause flag.

        Returns
        -------
        awsc.commander.Filterer
            Self.
        """
        self.paused = False
        return self

    def close(self):
        """
        Closes the filter bar and removes it from view.
        """
        self.parent.remove_block(self)
        self.paused = True
        self.session.filterer = None

    def paint(self):
        super().paint()
        (x0, x1), (y0, _) = self.inner
        Commons.UIInstance.print("/", xy=(x0 + 1, y0), color=self.symbol_color)
        space = (x1 - 1) - (x0 + 2) + 1
        text = self.text if len(self.text) <= space else self.text[:space]
        Commons.UIInstance.print(
            text,
            xy=(x0 + 2, y0),
            color=self.color if not self.paused else self.inactive_color,
        )


class Commander(Control):
    """
    The Commander is the command bar for switching between controls. It allows navigation between AWS resources by typing commands defined
    by the command_palette attribute of ResourceListers into the command bar.

    Attributes
    ----------
    session : awsc.session.Session
        The session manager object.
    color : awsc.termui.color.Color
        The color of the control's text and borders.
    symbol_color : awsc.termui.color.Color
        The color of the symbol for the filter bar.
    autocomplete_color : awsc.termui.color.Color
        The color of the autocompletion text in the bar.
    ok_color : awsc.termui.color.Color
        The color of the text in the bar when it fully matches a valid command.
    autocomplete_color : awsc.termui.color.Color
        The color of the text in the bar when it does not match a valid command and does not autocomplete to a valid command.
    paused : bool
        Whether the bar is inactive. The inactive bar still applies its filter, but pressing keys does not type into it.
    accepted_input : str
        The list of accepted input keys. Defaults to accepted textfield inputs.
    text : str
        The current filter.
    options : dict(str, callable() -> list(awsc.termui.control.Control))
        A mapping of valid options to their respective callbacks.
    """

    def __init__(
        self,
        *args,
        session,
        color,
        symbol_color,
        autocomplete_color,
        ok_color,
        error_color,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.session = session
        self.color = color
        self.symbol_color = symbol_color
        self.autocomplete_color = autocomplete_color
        self.ok_color = ok_color
        self.error_color = error_color
        self.session.commander = self
        self.accepted_input = Commons.TextfieldInputsAlphaNum
        self.text = ""
        self.options = session.commander_options

    def autocomplete(self):
        """
        Autocompletion callback. Returns the first autocompletion match for the text that has been typed. The first match is always the
        shortest possible match.

        Returns
        -------
        str
            The autocompleted command. None if nothing has been typed or no matches are found.
        """
        if len(self.text) == 0:
            return None
        opt_keys = self.options.keys()
        candidates = [cand for cand in opt_keys if cand.startswith(self.text.lower())]
        if len(candidates) > 0:
            candidates.sort(key=len)
            return candidates[0]
        return None

    def accept_autocomplete(self):
        """
        Called when the user accepts the autocompletion, by pressing TAB. Fills the command bar to the autocompletion.
        """
        acp = self.autocomplete()
        if acp is not None:
            self.text = acp

    def input(self, key):
        if key.is_sequence:
            if key.name == "KEY_ENTER":
                self.accept_and_close()
            elif key.name == "KEY_ESCAPE":
                self.close()
            elif key.name == "KEY_BACKSPACE":
                if len(self.text) > 0:
                    self.text = self.text[:-1]
            elif key.name == "KEY_DELETE":
                self.text = ""
            elif key.name == "KEY_TAB":
                self.accept_autocomplete()
            Commons.UIInstance.dirty = True
        elif str(key) in self.accepted_input:
            self.text += key
            Commons.UIInstance.dirty = True
        return True

    def accept_and_close(self):
        """
        Hotkey callback for pressing ENTER. If the text is a valid command in the bar, opens the associated control. If the command is not
        valid but autocompletes to a valid command, that command is used instead. If neither is valid, does nothing.
        """
        text = self.text.lower()
        option = None
        if text in self.options:
            option = self.options[text]
        else:
            acp = self.autocomplete()
            if acp is not None:
                option = self.options[acp]
        if option is not None:
            self.session.replace_frame(option())
            self.close()

    def close(self):
        """
        Closes the commander and removes it from view.
        """
        self.parent.remove_block(self)
        self.session.commander = None

    def paint(self):
        super().paint()
        (x0, x1), (y0, _) = self.inner
        Commons.UIInstance.print(":", xy=(x0 + 1, y0), color=self.symbol_color)
        space = (x1 - 1) - (x0 + 2) + 1
        text = self.text if len(self.text) <= space else self.text[:space]
        acp = self.autocomplete()
        color = self.color
        if self.text.lower() in self.options:
            color = self.ok_color
        elif acp is None:
            color = self.error_color
        Commons.UIInstance.print(text, xy=(x0 + 2, y0), color=color)
        if acp is not None:
            acp = acp[len(self.text) :]
            if len(acp) > 0:
                Commons.UIInstance.print(
                    acp, xy=(x0 + 2 + len(self.text), y0), color=self.autocomplete_color
                )
