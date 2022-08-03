import datetime

from .color import ColorDarkGreen, ColorGold
from .common import Commons
from .control import Control


class BarGraph(Control):
    DPB_ZeroOrLessToMax = 0
    DPB_ZeroToMax = 1
    DPB_MinToMax = 2

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        color=ColorGold,
        highlight_color=ColorDarkGreen,
        **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
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
        self.hotkeys = {
            "KEY_END": self.end,
            "KEY_HOME": self.home,
            "KEY_LEFT": self.scroll_left,
            "KEY_RIGHT": self.scroll_right,
        }
        self.tooltips = {}

        self.left = 0
        self.highlight = 0

    def input(self, key):
        inkey = str(key)
        if key.is_sequence:
            inkey = key.name
        else:
            inkey = inkey.lower()
        if inkey in self.hotkeys.keys():
            self.hotkeys[inkey](self)
            Commons.UIInstance.dirty = True
            return True
        return False

    def add_hotkey(self, hotkey, action, tooltip=None):
        self.hotkeys[hotkey] = action
        if tooltip is not None:
            self.tooltips[hotkey] = tooltip
        Commons.UIInstance.dirty = True

    def scroll_left(self, *args):
        if self.highlight > 0:
            self.highlight -= 1
            if self.left > self.highlight:
                self.left = self.highlight
            Commons.UIInstance.dirty = True

    def home(self, *args):
        self.left = 0
        self.highlight = 0
        Commons.UIInstance.dirty = True

    def end(self, *args):
        self.highlight = len(self.datapoints) - 1
        self.left = max(len(self.datapoints) - self.colspace, 0)
        Commons.UIInstance.dirty = True

    def scroll_right(self, *args):
        if self.highlight < len(self.datapoints) - 1:
            self.highlight += 1
            if self.highlight >= self.left + self.colspace:
                self.left += 1
            Commons.UIInstance.dirty = True

    @property
    def data_points_behaviour(self):
        return self._data_points_behaviour

    @data_points_behaviour.setter
    def data_points_behaviour(self, value):
        self._data_points_behaviour = value
        if value == BarGraph.DPB_ZeroOrLessToMax:
            self.min_point = 0
            for dp in self.datapoints:
                if dp[1] < self.min_point:
                    self.min_point = dp[1]
        elif value == BarGraph.DPB_ZeroToMax:
            self.min_point = 0
        elif value == BarGraph.DPB_MinToMax:
            self.min_point = self.max_point
            for dp in self.datapoints:
                if dp[1] < self.min_point:
                    self.min_point = dp[1]
        else:
            raise ValueError

    def add_datapoint(self, timestamp, datapoint):
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
            for i in range(len(self.datapoints)):
                ts = self.datapoints[i][0]
                if ts > timestamp:
                    self.datapoints.insert(i, (timestamp, datapoint))
                    return
            self.datapoints.append((timestamp, datapoint))
        finally:
            self.left = max(len(self.datapoints) - self.colspace, 0)
            self.highlight = len(self.datapoints) - 1
            Commons.UIInstance.dirty = True

    @Control.border.setter  # type: ignore[attr-defined]
    def border(self, value):
        self._border = value
        # Do not execute on border initialization
        if hasattr(self, "datapoints"):
            self.left = max(len(self.datapoints) - self.colspace, 0)
            Commons.UIInstance.dirty = True

    @property
    def colspace(self):
        c = self.corners()
        wspace = c[0][1] - c[0][0] + 1 - (0 if self.border is None else 2)
        max_label = "{0:.2f}".format(float(self.max_point))
        min_label = "{0:.2f}".format(float(self.min_point))
        x_label_space = max(len(max_label), len(min_label)) + 1
        return wspace - x_label_space

    def paint(self):
        super().paint()
        c = self.corners()
        wspace = c[0][1] - c[0][0] + 1 - (0 if self.border is None else 2)
        hspace = c[1][1] - c[1][0] + 1 - (0 if self.border is None else 2)
        x0 = c[0][0] + (0 if self.border is None else 1)
        y0 = c[1][0] + (0 if self.border is None else 1)

        max_label = "{0:.2f}".format(float(self.max_point))
        min_label = "{0:.2f}".format(float(self.min_point))

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
            "Value at {0}: {1:.2f}".format(
                self.datapoints[self.highlight][0].isoformat(),
                self.datapoints[self.highlight][1],
            ),
            (xb0, y0 + rowspace + 1),
            color=self.highlight_color,
        )

        v = self.max_point
        for y in range(y0, y0 + rowspace):
            row_bounds = (v - point_step, v)
            v -= point_step
            row = ["", "", ""]
            ri = 0
            rolling = 0
            for col in range(first_col, last_col + 1):
                datapoint = self.datapoints[col][1]
                colw = col_width
                if col == self.highlight:
                    ri = 1
                if rolling > 1:
                    colw += 1
                    rolling -= 1
                if datapoint < row_bounds[0]:
                    if row_bounds[0] > 0:
                        row[ri] += self.subdivisions[0] * colw
                    else:
                        row[ri] += self.subdivisions[-8] * colw
                elif datapoint > row_bounds[1]:
                    if row_bounds[1] > 0:
                        row[ri] += self.subdivisions[8] * colw
                    else:
                        row[ri] += self.subdivisions[0] * colw
                else:
                    if row_bounds[0] < 0 and row_bounds[1] > 0:
                        row[ri] += self.subdivisions[8] * colw
                    elif datapoint > 0:
                        if point_step != 0:
                            t = int((float(datapoint - row_bounds[0]) / point_step) * 8)
                        else:
                            t = "?"
                        row[ri] += self.subdivisions[t] * colw
                    else:
                        if point_step != 0:
                            t = int((float(datapoint - row_bounds[1]) / point_step) * 8)
                        else:
                            t = "?"
                        row[ri] += self.subdivisions[t] * colw
                rolling += roll
                if col == self.highlight:
                    ri = 2
            Commons.UIInstance.print(row[0], (xb0, y), color=self.color)
            if len(row[1]) > 0:
                Commons.UIInstance.print(
                    row[1], (xb0 + len(row[0]), y), color=self.highlight_color
                )
                if len(row[2]) > 0:
                    Commons.UIInstance.print(
                        row[2], (xb0 + len(row[0]) + len(row[1]), y), color=self.color
                    )
