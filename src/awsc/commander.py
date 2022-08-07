from .termui.common import Commons
from .termui.control import Control


class Filterer(Control):
    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        session,
        color,
        symbol_color,
        autocomplete_color,
        inactive_color,
        *args,
        **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        self.session = session
        self.color = color
        self.symbol_color = symbol_color
        self.autocomplete_color = autocomplete_color
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
        self.paused = True

    def resume(self):
        self.paused = False

    def close(self):
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
    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        session,
        color,
        symbol_color,
        autocomplete_color,
        ok_color,
        error_color,
        *args,
        **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
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
        if len(self.text) == 0:
            return None
        opt_keys = self.options.keys()
        candidates = [cand for cand in opt_keys if cand.startswith(self.text.lower())]
        if len(candidates) > 0:
            candidates.sort(key=len)
            return candidates[0]
        return None

    def accept_autocomplete(self):
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
