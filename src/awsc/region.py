"""
Module for region-related resources.
"""
from .base_control import OpenableListControl
from .common import Common
from .termui.list_control import ListEntry


class RegionList(OpenableListControl):
    """
    Lister control for available AWS regions.
    """

    prefix = "region_list"
    title = "Regions"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    @OpenableListControl.Autohotkey("d", "Set as default", True)
    def set_default_region(self, _):
        """
        Hotkey callback for setting the default region.
        """
        Common.Configuration["default_region"] = self.selection.name
        Common.Configuration.write_config()
        for entry in self.entries:
            if entry.name != Common.Configuration["default_region"]:
                entry["default"] = " "
            else:
                entry["default"] = "✓"

    @OpenableListControl.Autohotkey("KEY_ENTER", "Select", True)
    def select_region(self, _):
        """
        Hotkey callback for setting the active region.
        """
        Common.Session.region = self.selection.name
