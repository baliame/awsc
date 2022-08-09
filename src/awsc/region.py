from .base_control import OpenableListControl
from .common import Common
from .termui.list_control import ListEntry


class RegionList(OpenableListControl):
    prefix = "region_list"
    title = "Regions"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_hotkey("d", self.set_default_region, "Set as default")
        self.add_hotkey("KEY_ENTER", self.select_region, "Select region")
        self.add_column("usage frequency", 12)
        self.add_column("default", 8)
        regions = sorted(Common.Session.service_provider.list_regions())
        for region in regions:
            self.add_entry(
                ListEntry(
                    region,
                    **{
                        "usage frequency": 0,
                        "default": "✓"
                        if region == Common.Configuration["default_region"]
                        else " ",
                    }
                )
            )
        try:
            self.selected = regions.index(Common.Configuration["default_region"])
        except ValueError:
            self.selected = 0

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
