from .common import Common
from .info import HotkeyDisplay
from .termui.alignment import Dimension, TopRightAnchor
from .termui.list_control import ListControl, ListEntry


class RegionList(ListControl):
    def __init__(self, parent, alignment, dimensions, *args, **kwargs):
        super().__init__(
            parent,
            alignment,
            dimensions,
            color=Common.color("region_list_generic", "generic"),
            selection_color=Common.color("region_list_selection", "selection"),
            title_color=Common.color("region_list_heading", "column_title"),
            *args,
            **kwargs,
        )
        self.hotkey_display = HotkeyDisplay(
            self.parent,
            TopRightAnchor(1, 0),
            Dimension("33%|50", 8),
            self,
            session=Common.Session,
            highlight_color=Common.color("hotkey_display_title"),
            generic_color=Common.color("hotkey_display_value"),
        )
        self.add_hotkey("d", self.set_default_region, "Set as default")
        self.add_hotkey("KEY_ENTER", self.select_region, "Select region")
        self.add_column("usage frequency", 12)
        self.add_column("default", 8)
        idx = 0
        defa = 0
        for region in sorted(Common.Session.service_provider.list_regions()):
            if region == Common.Configuration["default_region"]:
                defa = idx
                d = "✓"
            else:
                d = " "
            self.add_entry(ListEntry(region, **{"usage frequency": 0, "default": d}))
            idx += 1
        self.selected = defa

    def set_default_region(self, _):
        if self.selection is not None:
            Common.Configuration["default_region"] = self.selection.name
            Common.Configuration.write_config()
            for entry in self.entries:
                if entry.name != Common.Configuration["default_region"]:
                    entry.columns["default"] = " "
                else:
                    entry.columns["default"] = "✓"

    def select_region(self, _):
        if self.selection is not None:
            Common.Session.region = self.selection.name
