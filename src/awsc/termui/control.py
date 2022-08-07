import threading

from .block import Block
from .common import Commons


class BorderStyle:
    def __init__(self, chars=None):
        if chars is None:
            chars = ["-", "|", "-", "-", "-", "-"]
        self.chars = chars

    @property
    def horizontal(self):
        return self.chars[0]

    @property
    def vertical(self):
        return self.chars[1]

    @property
    def topleft(self):
        return self.chars[2]

    @property
    def topright(self):
        return self.chars[3]

    @property
    def bottomleft(self):
        return self.chars[4]

    @property
    def bottomright(self):
        return self.chars[5]


BorderStyleContinuous = BorderStyle(["─", "│", "┌", "┐", "└", "┘"])


class Border:
    def __init__(
        self,
        style=None,
        color=None,
        title=None,
        title_color=None,
        title_info=None,
        title_info_color=None,
    ):
        self.style = style
        self.color = color
        self.title = title
        self.title_color = title_color
        self.title_info = title_info
        self.title_info_color = title_info_color

    def paint(self, block):
        if self.style is None or self.color is None:
            return
        corners = block.corners()
        dimensions = block.dimensions()
        for i in range(corners[1][0], corners[1][1] + 1):
            if i == corners[1][0]:
                if self.title is None or self.title_color is None:
                    outer = (
                        self.style.topleft
                        + self.style.horizontal * (dimensions[0] - 1)
                        + self.style.topright
                    )
                    Commons.UIInstance.print(
                        outer, xy=(corners[0][0], i), color=self.color
                    )
                else:
                    total_title = self.title
                    if self.title_info is not None:
                        total_title = f"{self.title} ({self.title_info})"
                    cpos = int((dimensions[0] + 1) / 2)
                    spos = cpos - int(len(total_title) / 2) - 1
                    slen = len(total_title) + 2
                    outer = self.style.topleft + self.style.horizontal * spos
                    length = len(outer)
                    Commons.UIInstance.print(
                        outer, xy=(corners[0][0], i), color=self.color
                    )
                    outer = " " + self.title + " "
                    Commons.UIInstance.print(
                        outer,
                        xy=(corners[0][0] + length, i),
                        color=self.title_color,
                        bold=True,
                    )
                    length += len(outer)
                    if self.title_info is not None:
                        Commons.UIInstance.print(
                            "(",
                            xy=(corners[0][0] + length, i),
                            color=self.title_color,
                            bold=True,
                        )
                        length += 1
                        Commons.UIInstance.print(
                            self.title_info,
                            xy=(corners[0][0] + length, i),
                            color=self.title_color
                            if self.title_info_color is None
                            else self.title_info_color,
                            bold=True,
                        )
                        length += len(self.title_info)
                        Commons.UIInstance.print(
                            ") ",
                            xy=(corners[0][0] + length, i),
                            color=self.title_color,
                            bold=True,
                        )
                        length += 2
                    outer = (
                        self.style.horizontal * (dimensions[0] - 1 - spos - slen)
                        + self.style.topright
                    )
                    Commons.UIInstance.print(
                        outer, xy=(corners[0][0] + length, i), color=self.color
                    )
            elif i == corners[1][1]:
                outer = (
                    self.style.bottomleft
                    + self.style.horizontal * (dimensions[0] - 1)
                    + self.style.bottomright
                )
                Commons.UIInstance.print(outer, xy=(corners[0][0], i), color=self.color)
            else:
                outer = (
                    self.style.vertical
                    + " " * (dimensions[0] - 1)
                    + self.style.vertical
                )
                Commons.UIInstance.print(outer, xy=(corners[0][0], i), color=self.color)


BorderNone = Border()


class Control(Block):
    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        weight=0,
        tag="default",
        border=None,
        **kwargs,
    ):
        super().__init__(
            parent, alignment, dimensions, *args, weight=weight, tag=tag, **kwargs
        )
        self.border = border
        self.thread_share = {}
        self.mutex = threading.Lock()

    @property
    def border(self):
        return self._border

    @border.setter
    def border(self, value):
        self._border = value
        Commons.UIInstance.dirty = True

    @property
    def inner(self):
        corners = self.corners()
        x0 = corners[0][0] + (0 if self.border is None else 1)
        x1 = corners[0][1] - (0 if self.border is None else 1)
        y0 = corners[1][0] + (0 if self.border is None else 1)
        y1 = corners[1][1] - (0 if self.border is None else 1)
        return ((x0, x1), (y0, y1))

    @property
    def w_in(self):
        return self.width if self.border is None else self.width - 2

    def paint(self):
        if self.border is not None:
            self.border.paint(self)
        super().paint()
