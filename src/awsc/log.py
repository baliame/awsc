"""
Module for logging-related controls.
"""
import datetime
import json
from operator import attrgetter

from .base_control import GenericDescriber, OpenableListControl, datetime_hack
from .common import Common
from .termui.list_control import ListEntry


class LogViewer(GenericDescriber):
    """
    Browser control for viewing log entries.
    """

    def __init__(self, *args, selection, **kwargs):
        columns = selection.copy()
        columns["context"] = json.loads(columns["context"])
        content = json.dumps(columns, default=datetime_hack, indent=2, sort_keys=True)
        super().__init__(
            *args,
            describing="logs",
            content=content,
            **kwargs,
        )


class LogLister(OpenableListControl):
    """
    Lister control for log entries.
    """

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
        """
        Inserts a new raw entry. Callback for the logholder for pushing entries into the lister.
        """
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
        self.entries.sort(reverse=True, key=attrgetter("raw_timestamp"))
        self._cache = None

    def on_close(self):
        """
        Cleanup hook. Detaches the control from the log storage.
        """
        self.logholder.detach()
