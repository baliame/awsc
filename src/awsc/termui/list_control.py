"""
This module defines list controls for displaying data in tables.
"""
import datetime

from .color import ColorBlackOnGold, ColorBlackOnOrange, ColorGold
from .common import Commons
from .control import HotkeyControl


class ListControl(HotkeyControl):
    """
    A ListControl is a large control which allows displaying any amount of entries as a list of rows, where each row is a set of columns.
    ListControls allow navigation and selection of items which in turn allows the use of hotkeys for operating on entries.

    Attributes
    ----------
    entries : list(awsc.termui.list_control.ListEntry)
        A list of entries.
    color : awsc.termui.color.Color
        The color of unselected list entries.
    selection_color : awsc.termui.color.Color
        The color of selected list entries.
    title_color : awsc.termui.color.Color
        The color of the title in the border bar.
    selected : int
        The index of the selected row.
    column_titles : dict
        A mapping of column titles to the size of the column. By default, this contains the initial size of the column. Space will be given to
        and taken away from columns roughly equally based on window size.
    column_order : list
        The order in which columns should be displayed. A column must be present in both column_order and column_titles to function properly.
    calculated : int
        Cached value for the block width for which column sizes have been calculated.
    _filter : str
        The currently set filter for filtering list entries.
    _cache : list
        Cache for the list of filtered entries.
    top : int
        How many entries should be skipped before displaying (how far we're scrolled down).
    update_color : awsc.termui.color.Color
        The color of rows that have been recently (in the past 5 seconds) updated.
    update_selection_color : awsc.termui.color.Color
        The color of rows that have been recently (in the past 5 seconds) updated and are selected.
    """

    def __init__(
        self,
        *args,
        color=ColorGold,
        selection_color=ColorBlackOnGold,
        title_color=ColorBlackOnOrange,
        update_color=ColorGold,
        update_selection_color=ColorBlackOnGold,
        **kwargs,
    ):
        """
        Initializes a ListControl object.
        """
        super().__init__(*args, **kwargs)
        self.entries = []
        self.color = color
        self.selection_color = selection_color
        self.title_color = title_color
        self.selected = 0
        self.column_titles = {"name": 30}
        self.column_order = ["name"]
        self.calculated = 0
        self._filter = None
        self.thread_share["clear"] = False
        self._cache = None
        self.thread_share["new_entries"] = []
        self.thread_share["finalize"] = False
        self.top = 0
        self.update_color = update_color
        self.update_selection_color = update_selection_color

    def validate_hotkey(self, key):
        return self.selection is not None

    @property
    def filter(self):
        """
        Allows for filtering the list entries without removing them. Only entries matching the filter are displayed.

        The filter will do a search in all fields of the entry, even hidden ones.
        """
        return self._filter

    @filter.setter
    def filter(self, value):
        Commons.UIInstance.dirty = True
        self._filter = value
        self.top = 0
        self.selected = 0
        self._cache = None

    def add_entry(self, entry):
        """
        Adds a new entry to the ListControl.

        Parameters
        ----------
        entry : awsc.termui.list_control.ListEntry
            The new entry to add.
        """
        self.entries.append(entry)
        self.sort()
        self._cache = None
        Commons.UIInstance.dirty = True

    @property
    def filtered(self):
        """
        Read-only property that returns the list of filtered entris.
        """
        if self._cache is None:
            self._cache = [e for e in self.entries if e.matches_filter(self._filter)]
        return self._cache

    @HotkeyControl.Autohotkey("KEY_DOWN")
    def list_down(
        self, *args
    ):  # pylint: disable=unused-argument # hotkey hooks will always be passed an extra argument
        """
        Hotkey callback for KEY_DOWN. Moves the selection cursor down by one row.
        """
        if self.selected < len(self.filtered) - 1:
            self.selected += 1
        rows = self.rows
        if self.selected >= self.top + rows:
            self.top = max(0, self.selected - rows + 1)

    @HotkeyControl.Autohotkey("KEY_UP")
    def list_up(
        self, *args
    ):  # pylint: disable=unused-argument # hotkey hooks will always be passed an extra argument
        """
        Hotkey callback for KEY_UP. Moves the selection cursor down by one row.
        """
        if self.selected > 0:
            self.selected -= 1
        if self.selected < self.top:
            self.top = self.selected

    @HotkeyControl.Autohotkey("KEY_PGDOWN")
    def pagedown(
        self, *args
    ):  # pylint: disable=unused-argument # hotkey hooks will always be passed an extra argument
        """
        Hotkey callback for KEY_PAGEDOWN. Moves the selection cursor down by one page - which is the number of visible rows.
        """
        self.selected += self.rows
        self.selected = min(len(self.filtered) - 1, self.selected)
        rows = self.rows
        if self.selected >= self.top + rows:
            self.top = max(0, self.selected - rows + 1)

    @HotkeyControl.Autohotkey("KEY_PGUP")
    def pageup(
        self, *args
    ):  # pylint: disable=unused-argument # hotkey hooks will always be passed an extra argument
        """
        Hotkey callback for KEY_PAGEUP. Moves the selection cursor up by one page - which is the number of visible rows.
        """
        self.selected -= self.rows
        self.selected = max(0, self.selected)
        if self.selected < self.top:
            self.top = self.selected

    @HotkeyControl.Autohotkey("KEY_HOME")
    def home(
        self, *args
    ):  # pylint: disable=unused-argument # hotkey hooks will always be passed an extra argument
        """
        Hotkey callback for KEY_HOME. Moves the selection cursor up to the first entry.
        """
        self.selected = 0
        self.top = 0

    @HotkeyControl.Autohotkey("KEY_END")
    def end(
        self, *args
    ):  # pylint: disable=unused-argument # hotkey hooks will always be passed an extra argument
        """
        Hotkey callback for KEY_END. Moves the selection cursor down to the last entry.
        """
        self.selected = len(self.filtered) - 1
        self.top = max(0, self.selected - self.rows + 1)

    @property
    def selection(self):
        """
        Read-only property which contains the currently selected list entry.

        Returns
        -------
        awsc.termui.list_control.ListEntry
            The currently selected ListEntry.
        """
        if len(self.filtered) > self.selected:
            return self.filtered[self.selected]
        return None

    @property
    def rows(self):
        """
        Read-only property which contains the number of visible rows in the control.

        Returns
        -------
        int
            Number of list entries that can be displayed at once.
        """
        corners = self.corners
        y0 = corners[1][0] + (0 if self.border is None else 1)
        y1 = corners[1][1] - (0 if self.border is None else 1)
        return y1 - y0

    def add_column(self, column, min_size=0, index=None):
        """
        Adds a new column to the ListControl.

        Parameters
        ----------
        column : str
            Name of the column to add.
        min_size : int, default=0
            The initial size of the column.
        index : int, optional
            The position where the column should be inserted. By default, the column is added as the last column.
        """
        if index is None:
            self.column_order.append(column)
        else:
            self.column_order.insert(index, column)
        self.column_titles[column] = min_size
        self.calculated = 0
        Commons.UIInstance.dirty = True

    def before_paint_critical(self):
        """
        Critical section for the pre-paint hook. This function holds the control mutex for its entire runtime.

        This function will call other critical section functions for handlers.
        """
        if self.thread_share["clear"]:
            Commons.UIInstance.dirty = True
            self.entries = []
            self.top = 0
            self.thread_share["clear"] = False
        if len(self.thread_share["new_entries"]) > 0:
            Commons.UIInstance.dirty = True
            self.handle_new_entries_critical(self.thread_share["new_entries"])
            self._cache = None
            self.thread_share["new_entries"] = []
        if self.thread_share["finalize"]:
            self.handle_finalization_critical()
            self.thread_share["finalize"] = False

    def handle_new_entries_critical(self, entries):
        """
        Critical section for the new entry hook. Called by before_paint_critical, therefore holds the control mutex.

        Parameters
        ----------
        entries : list(awsc.termui.list_control.ListEntry)
            A list of new entries to add to the control.
        """
        self.entries.extend(entries)
        self.sort()

    def handle_finalization_critical(self):
        """
        Critical section for the finalization of new entries. Called by before_paint_critical, therefore holds the control mutex.
        """

    def before_paint(self):
        super().before_paint()
        with self.mutex:
            self.before_paint_critical()
        # if self.selected >= len(self.entries):
        #  self.selected = len(self.entries) - 1
        # if self.selected < 0:
        #  self.selected = 0

    def sort(self):
        """
        Sorts the list of entries. Expected to be overridden by controls which actually understand how they want to sort their entries.

        Sorting happens automatically each time new entries are inserted.
        """

    def paint(self):
        win = self.w_in
        if win != self.calculated:
            vals = 0
            for _, value in self.column_titles.items():
                vals += value
            if vals > win:
                ratio = float(vals) / float(win)
                tot = 0
                # pylint: disable=consider-iterating-dictionary # Operation modifies dictionary
                for k in self.column_titles.keys():
                    self.column_titles[k] = int(float(self.column_titles[k]) / ratio)
                    tot += self.column_titles[k]
                rem = win - tot
                if "name" in self.column_titles:
                    self.column_titles["name"] += rem
                else:
                    self.column_titles[self.column_order[0]] += rem
            elif vals < win:
                diff = win - vals
                part = int(diff / len(self.column_titles))
                rem = diff - (part * len(self.column_titles))
                # pylint: disable=consider-iterating-dictionary # Operation modifies dictionary
                for k in self.column_titles.keys():
                    self.column_titles[k] += part
                if "name" in self.column_titles:
                    self.column_titles["name"] += rem
                else:
                    self.column_titles[self.column_order[0]] += rem
            self.calculated = win

        super().paint()
        corners = self.corners
        y = corners[1][0] + (0 if self.border is None else 1)
        x = corners[0][0] + (0 if self.border is None else 1)
        now = datetime.datetime.now()
        rows = self.rows
        for col in self.column_order:
            text = col
            maximum = self.column_titles[col]
            if len(col) > maximum:
                text = col[:maximum]
            elif len(col) < maximum:
                text = col + (int(maximum - len(col)) * " ")
            Commons.UIInstance.print(text.upper(), xy=(x, y), color=self.title_color)
            x += maximum
        y += 1
        for i in range(self.top, min(len(self.filtered), self.top + rows)):
            item = self.filtered[i]
            x = corners[0][0] + (0 if self.border is None else 1)
            for col in self.column_order:
                text = item[col]
                if text is None:
                    import sys

                    print(f"None encountered! Row: {item}", file=sys.stderr)
                maximum = self.column_titles[col]
                if len(text) > maximum:
                    text = text[:maximum]
                elif len(text) < maximum:
                    text = text + ((maximum - len(text)) * " ")
                if i == self.selected:
                    if now - item.updated < datetime.timedelta(seconds=3):
                        color = self.update_selection_color
                    else:
                        color = self.selection_color
                else:
                    if now - item.updated < datetime.timedelta(seconds=3):
                        color = self.update_color
                    else:
                        color = self.color
                Commons.UIInstance.print(text, xy=(x, y), color=color)
                x += maximum
            y += 1


class ListEntry(dict):
    """
    Represents a single entry in a ListControl. A fancy dict, if you will.

    Attributes
    ----------
    columns : dict
        A mapping of column name to column value.
    controller_data : object
        Arbitrary object which allows controlling ListControl derivative objects to store metadata associated with the list entry.
    updated : datetime.datetime
        The time this entry was last updated, to track when entries should be displayed as updated.
    """

    def __init__(self, name, controller_data=None, **kwargs):
        """
        Initializes a ListEntry.

        Parameters
        ----------
        name: str
            The initial value for the name field.
        controller_data : object, optional
            Arbitrary data.
        **kwargs : dict
            Each additional keyword argument will be treated as values for fields.
        """
        super().__init__(
            **{k: str(v) if v is not None else "" for k, v in kwargs.items()}
        )
        self.name = name
        if controller_data is None:
            self.controller_data = {}
        else:
            self.controller_data = controller_data
        self.updated = datetime.datetime.now()

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        if key in ("controller_data", "updated"):
            super().__setattr__(key, value)
        else:
            self[key] = value

    def __setitem__(self, key, value):
        if value is None:
            value = ""
        super().__setitem__(key, value)

    def matches_filter(self, filt):
        """
        Decider for whether the list entry matches a particular filter.

        Parameters
        ----------
        filt : str
            The filter to check.

        Returns
        -------
        bool
            Whether the list entry matches the given filter.
        """
        if filt is None:
            return True
        filt = filt.lower()
        for _, column in self.items():
            if filt in column.lower():
                return True
        return False

    def mutate(self, other):
        """
        Transforms a list entry into another list entry.
        Used by ListControl derivatives to update entries in-place based on periodic API queries, maintaining the updated timestamp.

        Parameters
        ----------
        other : awsc.termui.list_control.ListEntry
            The target ListEntry to transform this ListEntry into.
        """
        updated = False
        if self.name != other.name or len(self) != len(other):
            updated = True
        else:
            for col in self:
                if col not in other or self[col] != other[col]:
                    updated = True
                    break
        if not updated:
            return
        self.clear()
        self.update(other)
        self.updated = datetime.datetime.now()
        self.controller_data = other.controller_data
