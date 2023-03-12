"""
Module containing dashboard elements.
"""
from datetime import datetime, timedelta
from threading import Lock, Thread
from typing import Any, Dict, List, Type

from .base_control import DialogFieldResourceListSelector, OpenableListControl
from .common import Common, SessionAwareDialog, default_args, default_kwargs
from .hotkey import HotkeyDisplay
from .termui.alignment import Dimension, TopLeftDimensionAnchor
from .termui.control import HotkeyControl
from .termui.list_control import ListEntry
from .termui.ui import ControlCodes


class Dashboard(HotkeyControl):
    """
    Dashboard controller class. The dashboard contains a number of dashboard blocks organized in a table.
    """

    title = "Dashboard"
    prefix = "dashboard"

    block_registry: Dict[str, Type] = {}

    def __init__(self, *args, layout, **kwargs):
        super().__init__(*args, **kwargs)
        if len(layout) == 0:
            return
        self.refresh_loop = []
        self.load_layout(layout)
        self.add_hotkey(ControlCodes.R, self.force_refresh, "Refresh")
        self.add_hotkey("d", self.configure_default_layout, "Configure default")
        self.add_hotkey("c", self.configure_context_layout, "Configure context")
        self.hotkey_display = HotkeyDisplay.opener(caller=self)

    def reload_layout(self):
        """
        Callback for the configuration dialog to reload the dashboard.
        """
        self.load_layout(Common.Session.get_context_dashboard_layout())

    def configure_default_layout(self, *args):
        """
        Hotkey callback for configuring the default dashboard layout.
        """
        DashboardConfigurationDialog.opener(caller=self, is_default=True)

    def configure_context_layout(self, *args):
        """
        Hotkey callback for configuring the context dashboard layout.
        """
        DashboardConfigurationDialog.opener(caller=self, is_default=False)

    def load_layout(self, layout):
        """
        Reloads the dashboard with the layout configuration provided.

        Parameters
        ----------
        layout : list(list(str or class))
            The dashboard layout to load.
        """
        self.refresh_loop = []
        self.clear_blocks()
        h_perc = int(100.0 / len(layout))
        y = 0
        for row in layout:
            if len(row) == 0:
                continue
            w_perc = int(100.0 / len(row))
            x = 0
            for elem in row:
                cls = elem
                if isinstance(elem, str):
                    cls = Dashboard.block_registry[elem]
                self.refresh_loop.append(
                    cls(
                        self,
                        TopLeftDimensionAnchor(f"{w_perc * x}%", f"{h_perc * y}%"),
                        Dimension(f"{w_perc}%", f"{h_perc}%"),
                    )
                )
                x += 1
            y += 1

    def force_refresh(self, *args):
        """
        Forcibly refreshes blocks. Used for user input.
        """
        for elem in self.refresh_loop:
            elem.auto_refresh_data(True)

    def auto_refresh(self):
        """
        auto_refresh is called on top level blocks that have it automatically by the main loop.

        Checks periodically if subblocks need refreshing.
        """
        for elem in self.refresh_loop:
            elem.auto_refresh_data()

    @classmethod
    def opener(cls, layout=None, **kwargs):
        """
        Session-aware initializer for this class. Creates an ResourceLister object with the default alignment settings for the awsc
        layout.

        Returns
        -------
        list(awsc.base_control.OpenableListControl, awsc.info.HotkeyDisplay)
            A new instance of this class, and its associated hotkey display.
        """
        if layout is None:
            layout = Common.Session.get_context_dashboard_layout()
        instance = cls(
            *default_args(), **default_kwargs(cls.prefix), layout=layout, **kwargs
        )
        instance.border = Common.default_border(cls.prefix, cls.title, None)
        return [instance, instance.hotkey_display]

    @classmethod
    def register(cls):
        """
        Registers everything related to dashboards.
        """
        DashboardBlock.register()
        Common.Session.commander_options["dashboard"] = cls.opener
        Common.Session.commander_options["db"] = cls.opener


class DashboardConfigurationDialog(SessionAwareDialog):
    """
    Modal dialog for configuring the dashboard.
    """

    line_size = 20

    def __init__(self, *args, is_default=False, **kwargs):
        kwargs["border"] = Common.default_border("modal_dialog", "Layout configuration")
        super().__init__(*args, **kwargs)
        self.is_default = is_default

        layout = (
            Common.Session.get_default_dashboard_layout()
            if is_default
            else Common.Session.get_context_dashboard_layout()
        )
        if is_default:
            self.set_title_label("Configure layout for default dashboard")
        else:
            self.set_title_label(
                f"Configure dashboard layout for context {Common.Session.context}"
            )

        self.selectors = []

        # Currently, we assume all dashboards are 2x2. Later, this may change.
        for row in range(2):
            self.selectors.append([])
            for col in range(2):
                field = DialogFieldResourceListSelector(
                    DashboardBlockLister,
                    f"Dashboard row {row} block {col}",
                    default=layout[row][col],
                    primary_key="name",
                )
                self.selectors[row].append(field)
                self.add_field(field)

    def accept_and_close(self):
        config = Common.Session.config
        for row in self.selectors:
            for col in row:
                if col.value == "":
                    col.value = "Blank"
        if self.is_default:
            config["default_dashboard_layout"] = [
                [selector.value for selector in row] for row in self.selectors
            ]
        else:
            config["dashboard_layouts"][Common.Session.context] = [
                [selector.value for selector in row] for row in self.selectors
            ]
        config.write_config()
        Common.Session.set_message(
            "Successfully updated dashboard layout.", Common.color("message_success")
        )
        self.caller.reload_layout()
        super().accept_and_close()


class DashboardBlockLister(OpenableListControl):
    """
    Lister control for selecting dashboard blocks to add.
    """

    prefix = "dashboard_block"
    title = "Available Dashboard Blocks"

    def __init__(self, *args, selector_cb=None, **kwargs):
        super().__init__(
            *args,
            color=Common.color("dashboard_block_list_generic", "generic"),
            selection_color=Common.color("dashboard_block_list_selection", "selection"),
            title_color=Common.color("dashboard_block_list_heading", "column_title"),
            selector_cb=selector_cb,
            **kwargs,
        )

        self.add_column("classname", 12)
        self.add_column("description", 60)
        self.reload()

    def reload(self):
        """
        Reloads the list of available dashboard blocks.
        """
        self.entries = []
        for block, block_class in Dashboard.block_registry.items():
            if (
                block in ("DashboardBlock", "KeyValueDashboardBlock")
                or block_class.description == ""
            ):
                continue
            self.add_entry(
                ListEntry(
                    block,
                    **{
                        "classname": block,
                        "description": block_class.description,
                    },
                )
            )


class DashboardBlock(HotkeyControl):
    """
    Parent class for individual dashboard blocks. The intent of dashboard blocks is to display condensed information about a particular AWS service.

    Attributes
    ----------
    refresh_frequency : int
        How often (in seconds) to refresh the data displayed on the dashboard block automatically.
    """

    description = ""
    refresh_frequency = 30

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._refresh_frequency = timedelta(seconds=self.refresh_frequency)
        self.mutex = Lock()
        self.refreshing = False
        self.last_refresh = datetime.now()
        self.async_refresh()

    def async_refresh(self):
        """
        Async flow for refresh_data.
        """
        if self.refreshing:
            return
        self.refreshing = True
        thread = Thread(
            target=self._async_refresh_wrapper,
            daemon=True,
        )
        thread.start()

    def _async_refresh_wrapper(self):
        self.refresh_data()
        self.refreshing = False

    def auto_refresh_data(self, force=False):
        """
        Called by Dashboard to facilitate auto-refreshing.

        Parameters
        ----------
        force : bool, default=False
            Bypasses time checks if True.
        """
        if force or datetime.now() - self.last_refresh > self._refresh_frequency:
            self.async_refresh()
            self.last_refresh = datetime.now()

    def refresh_data(self):
        """
        Called automatically to refresh the data on the dashboard block. Subclasses are expected to override this.
        """

    @classmethod
    def register(cls):
        """
        Classmethod to register this class and all of its subclasses with the commander control.

        Also stores the class in the session control registry for other uses.

        This is why we can reach things via the command palette.
        """
        Dashboard.block_registry[cls.__name__] = cls
        for subcls in cls.__subclasses__():
            subcls.register()


class KeyValueDashboardBlock(DashboardBlock):
    """
    Key-value display template for dashboard blocks. Blocks that do nothing fancy, just display info, should use this.

    Attributes
    ----------
    info : dict
        A mapping of fields to field values. Refreshing the data should update this.
    status : int
        The current status of the block, comparable with the STATUS constants. Handling the status field is the responsibility of the
        subclass implementing refresh_data.
    labels : dict
        A mapping of fields to field labels for display purposes. Only fields present in labels, order and info will be rendered.
    order : list
        A list of fields. The order in which fields should be rendered.
    thresholds : dict
        A mapping of fields to threshold definitions. A threshold definition is a list alternating color names and numeric values. The first and the last element
        must always be a color. The color represents the color to print the value with if it's less than the next numeric value in the list, but greater than the
        previous numeric value of the list. There is an assumed negative infinity at the beginning, and positive infinity at the end of the list.
    suffixes : dict
        A mapping of field names to suffixes to render after the field value.
    inverted : list
        A list of field names where the label should be printed after the field value.
    additional_lines : list(tuple)
        A list of additional lines to display at the end of the block. Each entry in the list is a tuple in the format of (str, str, bool), where the first entry
        is the line to display, the second is the name of the color for the line, and the third is whether the line should be bold.
    """

    STATUS_LOADING = 0
    """
    Status value which represents that the block data is still loading.
    """

    STATUS_ERROR = 1
    """
    Status value which represents that the block data failed to load in the last refresh cycle.
    """

    STATUS_READY = 2
    """
    Status value which represents that the block data succeeded to load in the last refresh cycle.
    """

    labels: Dict[str, str] = {}
    order: List[str] = []
    thresholds: Dict[str, List[Any]] = {}
    suffixes: Dict[str, str] = {}
    inverted: List[str] = []

    def __init__(self, *args, **kwargs):
        self.info = {}
        self.additional_lines = []
        self.status = self.STATUS_LOADING
        super().__init__(*args, **kwargs)

    def paint(self):
        super().paint()
        with self.mutex:
            bounds = self.corners
            Common.Session.ui.print(
                self.description,
                xy=(bounds[0][0] + 1, bounds[1][0] + 1),
                bounds=bounds,
                color=Common.color("dashboard_block_label"),
                bold=True,
            )
            if self.status == self.STATUS_LOADING:
                Common.Session.ui.print_centered(
                    "Loading...",
                    bounds,
                    color=Common.color("dashboard_block_loading"),
                    bold=True,
                )
            elif self.status == self.STATUS_ERROR:
                Common.Session.ui.print_centered(
                    "Error loading data!",
                    bounds,
                    color=Common.color("dashboard_block_error"),
                    bold=True,
                )
            else:
                y = bounds[1][0] + 3
                for field in self.order:
                    if field not in self.info or field not in self.labels:
                        continue
                    x = bounds[0][0] + 1
                    if field not in self.inverted:
                        output = f"{self.labels[field]}: "
                        Common.Session.ui.print(
                            output,
                            xy=(x, y),
                            bounds=bounds,
                            color=Common.color("dashboard_block_label"),
                            bold=True,
                        )
                        x += len(output)
                    if field in self.thresholds:
                        is_color = True
                        for elem in self.thresholds[field]:
                            if is_color:
                                color = Common.color(elem)
                            else:
                                if self.info[field] < elem:
                                    break
                            is_color = not is_color
                    else:
                        color = Common.color("dashboard_block_information")
                    output = str(self.info[field])
                    if field in self.suffixes:
                        output = f"{output}{self.suffixes[field]}"
                    Common.Session.ui.print(
                        output,
                        xy=(x, y),
                        bounds=bounds,
                        color=color,
                        bold=False,
                    )
                    x += len(output)
                    if field in self.inverted:
                        output = f" {self.labels[field]}"
                        Common.Session.ui.print(
                            output,
                            xy=(x, y),
                            color=Common.color("dashboard_block_label"),
                            bold=True,
                            bounds=bounds,
                        )
                    y += 1
                for line in self.additional_lines:
                    x = bounds[0][0] + 1
                    output = line[0]
                    color = Common.color(line[1])
                    bold = line[2]
                    Common.Session.ui.print(
                        output,
                        xy=(x, y),
                        color=color,
                        bold=bold,
                        bounds=bounds,
                    )
                    y += 1

                if self.refreshing:
                    Common.Session.ui.print_centered(
                        "Refreshing...",
                        bounds,
                        color=Common.color("dashboard_block_loading"),
                        bold=True,
                    )


class Blank(DashboardBlock):
    """
    Alias for DashboardBlock. Does nothing, just occupies space.
    """

    description = "Blank space"

    def paint(self):
        super().paint()
        Common.Session.ui.print_centered(
            "Empty dashboard block",
            self.corners,
            color=Common.color("dashboard_block_label"),
            bold=True,
        )
