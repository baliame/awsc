import datetime
import json

import yaml

from .base_control import GenericDescriber, datetime_hack
from .common import Common, DefaultAnchor, DefaultBorder, DefaultDimension
from .info import HotkeyDisplay
from .termui.alignment import Dimension, TopRightAnchor
from .termui.list_control import ListControl, ListEntry


class LogLister(ListControl):
    @classmethod
    def opener(cls, **kwargs):
        l = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            **kwargs,
        )
        l.border = DefaultBorder("log", "Logs", None)
        return [l, l.hotkey_display]

    @classmethod
    def selector(cls, cb, **kwargs):
        return cls.opener(**{"selector_cb": cb, **kwargs})

    def __init__(
        self, parent, alignment, dimensions, *args, selector_cb=None, **kwargs
    ):
        super().__init__(
            parent,
            alignment,
            dimensions,
            color=Common.color("ssh_key_list_generic", "generic"),
            selection_color=Common.color("ssh_key_list_selection", "selection"),
            title_color=Common.color("ssh_key_list_heading", "column_title"),
            *args,
            **kwargs,
        )
        self.selector_cb = selector_cb
        self.hotkey_display = HotkeyDisplay(
            self.parent,
            TopRightAnchor(1, 0),
            Dimension("33%|50", 8),
            self,
            session=Common.Session,
            highlight_color=Common.color("hotkey_display_title"),
            generic_color=Common.color("hotkey_display_value"),
        )
        self.add_hotkey("d", self.describe, "Show full entry")
        if selector_cb is not None:
            self.add_hotkey("KEY_ENTER", self.select_and_close, "Select and close")
        else:
            self.add_hotkey("KEY_ENTER", self.describe, "Show full entry")
        self.add_column("type", 12)
        self.add_column("category", 20)
        self.add_column("subcategory", 20)
        self.add_column("resource", 20)
        self.add_column("timestamp", 20)
        self.logholder = Common._logholder
        self.logholder.attach(self)

    def add_raw_entry(self, entry):
        self.add_entry(
            ListEntry(
                entry["summary"],
                **{
                    "category": entry["category"],
                    "subcategory": entry["subcategory"]
                    if "subcategory" in entry
                    and entry["subcategory"] is not None
                    and entry["subcategory"] != "null"
                    else "<n/a>",
                    "resource": entry["resource"]
                    if entry["resource"] is not None
                    else "",
                    "type": entry["type"],
                    "timestamp": datetime.datetime.utcfromtimestamp(
                        entry["timestamp"]
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "raw_timestamp": entry["timestamp"],
                    "message": entry["message"],
                    "context": entry["context"] if "context" in entry else {},
                },
            )
        )

    def describe(self, _):
        if self.selection is not None:
            Common.Session.push_frame(LogViewer.opener(log_line=self.selection))

    def select_and_close(self, _):
        if self.selection is not None and self.selector_cb is not None:
            self.selector_cb(self.selection["name"])
            Common.Session.pop_frame()

    def sort(self):
        self.entries.sort(reverse=True, key=lambda x: x.columns["raw_timestamp"])
        self._cache = None

    def on_close(self):
        self.logholder.detach()


class LogViewer(GenericDescriber):
    def __init__(self, parent, alignment, dimensions, *args, log_line, **kwargs):
        columns = log_line.columns.copy()
        columns["context"] = json.loads(columns["context"])
        content = json.dumps(columns, default=datetime_hack, indent=2, sort_keys=True)
        super().__init__(
            parent,
            alignment,
            dimensions,
            describing="logs",
            content=content,
            **kwargs,
        )
