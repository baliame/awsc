from .common import Common, DefaultAnchor, DefaultBorder, DefaultDimension
from .info import HotkeyDisplay
from .termui.alignment import Dimension, TopRightAnchor
from .termui.list_control import ListControl, ListEntry


class CommanderOptionsLister(ListControl):
    title = "Commands"

    @classmethod
    def opener(cls, **kwargs):
        l = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            **kwargs,
        )
        l.border = DefaultBorder("help", "Commands", None)
        return [l, l.hotkey_display]

    def __init__(self, parent, alignment, dimensions, *args, **kwargs):
        super().__init__(
            parent,
            alignment,
            dimensions,
            color=Common.color("help_list_generic", "generic"),
            selection_color=Common.color("help_list_selection", "selection"),
            title_color=Common.color("help_list_heading", "column_title"),
            *args,
            **kwargs,
        )
        self.phony = {
            "ctx": "AWS Contexts",
            "context": "AWS Contexts",
            "region": "AWS Region",
            "ssh": "SSH Keys",
            "logs": "Logs",
        }
        self.hotkey_display = HotkeyDisplay(
            self.parent,
            TopRightAnchor(1, 0),
            Dimension("33%|50", 8),
            self,
            session=Common.Session,
            highlight_color=Common.color("hotkey_display_title"),
            generic_color=Common.color("hotkey_display_value"),
        )
        self.add_hotkey("KEY_ENTER", self.select_and_close, "Open")
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
                le = ListEntry(cmd, command=cmd, resource=opt.__self__.title)
            elif cmd in self.phony:
                le = ListEntry(cmd, command=cmd, resource=self.phony[cmd])
            else:
                le = ListEntry(cmd, command=cmd, resource="")
            le.controller_data["fn"] = opt
            self.entries.append(le)
        self.entries.sort(key=lambda x: x["command"])

    def select_and_close(self, _):
        if self.selection is not None:
            Common.Session.replace_frame(self.selection.controller_data["fn"]())
