from .base_control import OpenableListControl
from .common import Common
from .termui.list_control import ListEntry


class CommanderOptionsLister(OpenableListControl):
    title = "Commands"
    prefix = "help"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.phony = {}
        self.column_titles = {}
        self.column_order = []
        self.add_column("command", 12)
        self.add_column("resource", 48)
        self.reload()

    def reload(self, move=True):
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

    def select_and_close(self, _):
        if self.selection is not None:
            Common.Session.replace_frame(self.selection.controller_data["fn"]())
