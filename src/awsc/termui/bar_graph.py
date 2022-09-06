"""
This module defines a bar graph control that can be used to display timeseries.
"""
import datetime

from .color import ColorDarkGreen, ColorGold
from .common import Commons
from .control import HotkeyControl


class BarGraph(HotkeyControl):
    """
    In the most particular culmination of horrible ideas, this control attempts to - remarkably successfully, if I might add - display a bar
    graph in a terminal environment. It is fully capable of displaying a timestamped time series in an understandable fashion.

    Attributes
    ----------
    DPB_ZeroOrLessToMax : int
        Data point behaviour constant. Bar graphs with this data point behaviour will extend their min-point to the negative numbers if any
        datapoint is negative, but will never place their min-point higher than zero.
    DPB_ZeroToMax : int
        Data point behaviour constant. Bar graphs with this data point behaviour will always place their min-point at zero, even if some
        datapoints are negative. Negative datapoints will be displayed as an empty bar.
    DPB_MinToMax : int
        Data point behaviour constant. Bar graphs with this data point behaviour will always place their min-point at the value of the lowest
        datapoint, regardless of whether it is negative, zero or positive.
    subdivisions : dict
        The characters used to represent subdivisions of a single character cell. The key zero represents an empty cell, positive numbers up
        to 8 represent that many eighths of a cell to be filled on a bar extending upwards, while negative numbers are the same down to -8
        for a bar extending downwards. The question mark represents cells where something went horribly wrong.
    datapoints : list(tuple(datetime.datetime, float))
        A list of datapoints in the time series. Each datapoint is a tuple of the time of measuring, and the value of the datapoint.
    max_point : float
        The calculated highest datapoint in the graph.
    min_point : float
        The calculated lowest datapoint in the graph.
    color : awsc.termui.color.Color
        The main color to use for text and unselected columns.
    highlight_color : awsc.termui.color.Color
        The color to use for highlighted columns.
    left : int
        The offset for how many columns to skip before drawing - basically, the amount you are scrolled to the right by.
    highlight : int
        The index of the selected column.
    """

    DPB_ZeroOrLessToMax = 0
    DPB_ZeroToMax = 1
    DPB_MinToMax = 2

    def __init__(
        self,
        *args,
        color=ColorGold,
        highlight_color=ColorDarkGreen,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.subdivisions = {
            0: " ",
            1: "▁",
            2: "▂",
            3: "▃",
            4: "▄",
            5: "▅",
            6: "▆",
            7: "▇",
            8: "█",
            -1: "▔",
            -2: "▔",
            -3: "▔",
            -4: "▀",
            -5: "▀",
            -6: "▀",
            -7: "▀",
            -8: "█",
            "?": "░",
        }

        self._data_points_behaviour = BarGraph.DPB_ZeroOrLessToMax

        self.datapoints = []
        self.max_point = 0
        self.min_point = 0
        now = datetime.datetime.now()
        self.min_time = now
        self.max_time = now
        self.color = color
        self.highlight_color = highlight_color
        self.add_hotkey("KEY_END", self.end)
        self.add_hotkey("KEY_HOME", self.home)
        self.add_hotkey("KEY_LEFT", self.scroll_left)
        self.add_hotkey("KEY_RIGHT", self.scroll_right)

        self.left = 0
        self.highlight = 0

    def scroll_left(self, *args):
        """
        Hotkey callback for KEY_LEFT. Moves the selection one column to the left.
        """
        if self.highlight > 0:
            self.highlight -= 1
            if self.left > self.highlight:
                self.left = self.highlight
            Commons.UIInstance.dirty = True

    def home(self, *args):
        """
        Hotkey callback for KEY_HOME. Moves the selection all the way to the left.
        """
        self.left = 0
        self.highlight = 0
        Commons.UIInstance.dirty = True

    def end(self, *args):
        """
        Hotkey callback for KEY_END. Moves the selection all the way to the right.
        """
        self.highlight = len(self.datapoints) - 1
        self.left = max(len(self.datapoints) - self.colspace, 0)
        Commons.UIInstance.dirty = True

    def scroll_right(self, *args):
        """
        Hotkey callback for KEY_RIGHT. Moves the selection one column to the right.
        """
        if self.highlight < len(self.datapoints) - 1:
            self.highlight += 1
            if self.highlight >= self.left + self.colspace:
                self.left += 1
            Commons.UIInstance.dirty = True

    @property
    def data_points_behaviour(self):
        """
        Property representing the data points behaviour of this bar graph. Can be set to one of the data points behaviour constants defined
        in this class. Controls how the minimum point on the graph is determined when painting the graph.

        Raises
        ------
        ValueError
            The datapoint behaviour being set is not one of the allowed values.
        """
        return self._data_points_behaviour

    @data_points_behaviour.setter
    def data_points_behaviour(self, value):
        self._data_points_behaviour = value
        if value == BarGraph.DPB_ZeroOrLessToMax:
            self.min_point = 0
            for datapoint in self.datapoints:
                if datapoint[1] < self.min_point:
                    self.min_point = datapoint[1]
        elif value == BarGraph.DPB_ZeroToMax:
            self.min_point = 0
        elif value == BarGraph.DPB_MinToMax:
            self.min_point = self.max_point
            for datapoint in self.datapoints:
                if datapoint[1] < self.min_point:
                    self.min_point = datapoint[1]
        else:
            raise ValueError

    def add_datapoint(self, timestamp, datapoint):
        """
        Inserts a new datapoint into the bar graph.

        Parameters
        ----------
        timestamp : datetime.datetime
            The time of measurement for the datapoint.
        datapoint : float
            The value at the time of the measurement.
        """
        try:
            if len(self.datapoints) == 0:
                self.max_point = datapoint
                if self._data_points_behaviour == BarGraph.DPB_ZeroOrLessToMax:
                    self.min_point = min(0, datapoint)
                elif self._data_points_behaviour == BarGraph.DPB_ZeroToMax:
                    self.min_point = 0
                elif self._data_points_behaviour == BarGraph.DPB_MinToMax:
                    self.min_point = datapoint
            else:
                self.max_point = max(self.max_point, datapoint)
                if self._data_points_behaviour == BarGraph.DPB_ZeroOrLessToMax:
                    self.min_point = min(self.min_point, min(0, datapoint))
                elif self._data_points_behaviour == BarGraph.DPB_ZeroToMax:
                    self.min_point = 0
                elif self._data_points_behaviour == BarGraph.DPB_MinToMax:
                    self.min_point = min(self.min_point, datapoint)
            for idx, existing_datapoint in enumerate(self.datapoints):
                existing_timestamp = existing_datapoint[0]
                if existing_timestamp > timestamp:
                    self.datapoints.insert(idx, (timestamp, datapoint))
                    return
            self.datapoints.append((timestamp, datapoint))
        finally:
            self.left = max(len(self.datapoints) - self.colspace, 0)
            self.highlight = len(self.datapoints) - 1
            Commons.UIInstance.dirty = True

    @HotkeyControl.border.setter  # type: ignore[attr-defined]
    def border(self, value):
        self._border = value
        # Do not execute on border initialization
        if hasattr(self, "datapoints"):
            self.left = max(len(self.datapoints) - self.colspace, 0)
            Commons.UIInstance.dirty = True

    @property
    def colspace(self):
        """
        Read-only property representing the amount of displayable columns. This is shorter than the inner width of the control as there
        is a label for the minimum and maximum values on the graph.
        """
        corners = self.corners
        wspace = corners[0][1] - corners[0][0] + 1 - (0 if self.border is None else 2)
        max_label = f"{float(self.max_point):.2f}"
        min_label = f"{float(self.min_point):.2f}"
        x_label_space = max(len(max_label), len(min_label)) + 1
        return wspace - x_label_space

    def paint(self):
        super().paint()
        corners = self.corners
        wspace = corners[0][1] - corners[0][0] + 1 - (0 if self.border is None else 2)
        hspace = corners[1][1] - corners[1][0] + 1 - (0 if self.border is None else 2)
        x0 = corners[0][0] + (0 if self.border is None else 1)
        y0 = corners[1][0] + (0 if self.border is None else 1)

        max_label = f"{float(self.max_point):.2f}"
        min_label = f"{float(self.min_point):.2f}"

        x_label_space = max(len(max_label), len(min_label)) + 1
        colspace = wspace - x_label_space
        if colspace == 0:
            return
        first_col = self.left
        last_col = min(self.left + colspace - 1, len(self.datapoints) - 1)
        col_width = float(colspace) / float((last_col - first_col + 1))
        roll = col_width - int(col_width)
        col_width = int(col_width)
        rolling = 0

        rowspace = hspace - 2
        if rowspace == 0:
            return
        point_step = (self.max_point - self.min_point) / rowspace

        xb0 = x0 + x_label_space

        Commons.UIInstance.print(max_label, (x0, y0), color=self.color)
        Commons.UIInstance.print(min_label, (x0, y0 + rowspace - 1), color=self.color)
        Commons.UIInstance.print(
            self.datapoints[first_col][0].isoformat(),
            (xb0, y0 + rowspace),
            color=self.color,
        )
        last_ts = self.datapoints[last_col][0].isoformat()
        Commons.UIInstance.print(
            last_ts,
            (xb0 + colspace - len(last_ts) - 1, y0 + rowspace),
            color=self.color,
        )
        Commons.UIInstance.print(
            f"Value at {self.datapoints[self.highlight][0].isoformat()}: {self.datapoints[self.highlight][1]:.2f}",
            (xb0, y0 + rowspace + 1),
            color=self.highlight_color,
        )

        value = self.max_point
        for y in range(y0, y0 + rowspace):
            row_bounds = (value - point_step, value)
            value -= point_step
            row = ["", "", ""]
            rowindex = 0
            rolling = 0
            for col in range(first_col, last_col + 1):
                datapoint = self.datapoints[col][1]
                colw = col_width
                if col == self.highlight:
                    rowindex = 1
                if rolling > 1:
                    colw += 1
                    rolling -= 1
                if datapoint < row_bounds[0]:
                    if row_bounds[0] > 0:
                        row[rowindex] += self.subdivisions[0] * colw
                    else:
                        row[rowindex] += self.subdivisions[-8] * colw
                elif datapoint > row_bounds[1]:
                    if row_bounds[1] > 0:
                        row[rowindex] += self.subdivisions[8] * colw
                    else:
                        row[rowindex] += self.subdivisions[0] * colw
                else:
                    if row_bounds[0] < 0 < row_bounds[1]:
                        row[rowindex] += self.subdivisions[8] * colw
                    elif datapoint > 0:
                        if point_step != 0:
                            subdivision = int(
                                (float(datapoint - row_bounds[0]) / point_step) * 8
                            )
                        else:
                            subdivision = "?"
                        row[rowindex] += self.subdivisions[subdivision] * colw
                    else:
                        if point_step != 0:
                            subdivision = int(
                                (float(datapoint - row_bounds[1]) / point_step) * 8
                            )
                        else:
                            subdivision = "?"
                        row[rowindex] += self.subdivisions[subdivision] * colw
                rolling += roll
                if col == self.highlight:
                    rowindex = 2
            Commons.UIInstance.print(row[0], (xb0, y), color=self.color)
            if len(row[1]) > 0:
                Commons.UIInstance.print(
                    row[1], (xb0 + len(row[0]), y), color=self.highlight_color
                )
                if len(row[2]) > 0:
                    Commons.UIInstance.print(
                        row[2], (xb0 + len(row[0]) + len(row[1]), y), color=self.color
                    )
