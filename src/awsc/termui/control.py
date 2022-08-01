import threading

from .block import Block
from .common import Commons


class BorderStyle:
    def __init__(self, chars=["-", "|", "-", "-", "-", "-"]):
        self.chars = chars

    @property
    def horizontal(self):
        return self.chars[0]

    @property
    def vertical(self):
        return self.chars[1]

    @property
    def TL(self):
        return self.chars[2]

    @property
    def TR(self):
        return self.chars[3]

    @property
    def BL(self):
        return self.chars[4]

    @property
    def BR(self):
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
                        self.style.TL
                        + self.style.horizontal * (dimensions[0] - 1)
                        + self.style.TR
                    )
                    Commons.UIInstance.print(
                        outer, xy=(corners[0][0], i), color=self.color
                    )
                else:
                    total_title = self.title
                    if self.title_info is not None:
                        total_title = "{0} ({1})".format(self.title, self.title_info)
                    cpos = int((dimensions[0] + 1) / 2)
                    spos = cpos - int(len(total_title) / 2) - 1
                    slen = len(total_title) + 2
                    outer = self.style.TL + self.style.horizontal * spos
                    l = len(outer)
                    Commons.UIInstance.print(
                        outer, xy=(corners[0][0], i), color=self.color
                    )
                    outer = " " + self.title + " "
                    Commons.UIInstance.print(
                        outer,
                        xy=(corners[0][0] + l, i),
                        color=self.title_color,
                        bold=True,
                    )
                    l += len(outer)
                    if self.title_info is not None:
                        Commons.UIInstance.print(
                            "(",
                            xy=(corners[0][0] + l, i),
                            color=self.title_color,
                            bold=True,
                        )
                        l += 1
                        Commons.UIInstance.print(
                            self.title_info,
                            xy=(corners[0][0] + l, i),
                            color=self.title_color
                            if self.title_info_color is None
                            else self.title_info_color,
                            bold=True,
                        )
                        l += len(self.title_info)
                        Commons.UIInstance.print(
                            ") ",
                            xy=(corners[0][0] + l, i),
                            color=self.title_color,
                            bold=True,
                        )
                        l += 2
                    outer = (
                        self.style.horizontal * (dimensions[0] - 1 - spos - slen)
                        + self.style.TR
                    )
                    Commons.UIInstance.print(
                        outer, xy=(corners[0][0] + l, i), color=self.color
                    )
            elif i == corners[1][1]:
                outer = (
                    self.style.BL
                    + self.style.horizontal * (dimensions[0] - 1)
                    + self.style.BR
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
        weight=0,
        tag="default",
        border=None,
        *args,
        **kwargs
    ):
        super().__init__(parent, alignment, dimensions, weight, tag, *args, **kwargs)
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
        c = self.corners()
        x0 = c[0][0] + (0 if self.border is None else 1)
        x1 = c[0][1] - (0 if self.border is None else 1)
        y0 = c[1][0] + (0 if self.border is None else 1)
        y1 = c[1][1] - (0 if self.border is None else 1)
        return ((x0, x1), (y0, y1))

    @property
    def w_in(self):
        return self.w if self.border is None else self.w - 2

    def paint(self):
        if self.border is not None:
            self.border.paint(self)
        super().paint()
