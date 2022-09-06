"""
Module for meta controls.
"""
from .base_control import OpenableListControl
from .common import Common
from .termui.list_control import ListEntry


class CommanderOptionsLister(OpenableListControl):
    """
    List page for available command palette options.

    Attributes
    ----------
    phony : dict
        Deprecated. Legacy map of commands mapped to titles for bare ListControl subclasses.
    """

    title = "Commands"
    prefix = "help"

    def __init__(self, *args, **kwargs):
        """
        Initializes a CommanderOptionsLister.
        """
        super().__init__(*args, **kwargs)
        self.phony = {}
        self.column_titles = {}
        self.column_order = []
        self.add_column("command", 12)
        self.add_column("resource", 48)
        self.reload()

    def reload(self):
        """
        Reloads the list of available commands, repopulating the control.
        """
        self.entries = []
        for cmd in Common.Session.commander_options:
            opt = Common.Session.commander_options[cmd]
            if hasattr(opt, "__self__"):
                list_entry = ListEntry(cmd, command=cmd, resource=opt.__self__.title)
            elif cmd in self.phony:
                list_entry = ListEntry(cmd, command=cmd, resource=self.phony[cmd])
            else:
                list_entry = ListEntry(cmd, command=cmd, resource="")
            list_entry.controller_data["fn"] = opt
            self.entries.append(list_entry)
        self.entries.sort(key=lambda x: x["command"])

    @OpenableListControl.Autohotkey("KEY_ENTER", "Open", True)
    def open(self, _):
        """
        Hotkey callback for opening the list control for the current selection.
        """
        Common.Session.replace_frame(self.selection.controller_data["fn"]())
