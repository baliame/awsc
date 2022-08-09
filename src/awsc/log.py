import datetime
import json

from .base_control import GenericDescriber, OpenableListControl, datetime_hack
from .common import Common
from .termui.list_control import ListEntry


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


class LogLister(OpenableListControl):
    prefix = "log"
    title = "Logs"
    describer = LogViewer.opener

    def __init__(self, parent, alignment, dimensions, *args, **kwargs):
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

    def sort(self):
        self.entries.sort(reverse=True, key=lambda x: x.columns["raw_timestamp"])
        self._cache = None

    def on_close(self):
        self.logholder.detach()
