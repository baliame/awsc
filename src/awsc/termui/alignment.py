from .common import Commons


class Dimension:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def __getitem__(self, key):
        if key not in (0, 1, "x", "y", "w", "h"):
            raise KeyError("Bad dimension key " + key)
        val = self()
        return val[0] if key in (0, "x", "w") else val[1]

    def _v(self, value, height):
        if isinstance(value, str):
            test = value.split("|")
            if len(test) > 1:
                return max(self._v(test_value, height) for test_value in test)
            test = value.split("-")
            if len(test) > 1:
                val = self._v(test[0], height)
                for i in range(1, len(test)):
                    val -= self._v(test[i], height)
                return val
            if value[-1] == "%":
                return int(height * float(value[:-1]) / 100) - 1
        return int(value)

    def __call__(self):
        dim = Commons.UIInstance.dim
        width = self._v(self.width, dim[0])
        height = self._v(self.height, dim[1])
        return (width, height)


class TopLeftAnchor:
    def __init__(self, left, top):
        self.top = top
        self.left = left

    def anchor(self, parent):
        if parent is None:
            return (self.left, self.top)
        tlp = parent.topleft()
        return (tlp[0] + self.left, tlp[1] + self.top)

    def topleft(self, dim, parent):
        return self.anchor(parent)


class BottomLeftAnchor:
    def __init__(self, left, bottom):
        self.bottom = bottom
        self.left = left

    def anchor(self, parent):
        if parent is None:
            return (self.left, self.bottom)
        tlp = parent.topleft()
        brp = parent.bottomright()
        return (tlp[0] + self.left, brp[1] - self.bottom)

    def topleft(self, dim, parent):
        anchor = self.anchor(parent)
        return (anchor[0], anchor[1] - dim[1] + 1)


class TopRightAnchor:
    def __init__(self, right, top):
        self.top = top
        self.right = right

    def anchor(self, parent):
        if parent is None:
            return (self.right, self.top)
        tlp = parent.topleft()
        brp = parent.bottomright()
        return (brp[0] - self.right, tlp[1] + self.top)

    def topleft(self, dim, parent):
        anchor = self.anchor(parent)
        return (anchor[0] - dim[0] + 1, anchor[1])


class CenterAnchor:
    def __init__(self, xoffset, yoffset):
        self.xoffset = xoffset
        self.yoffset = yoffset

    def anchor(self, parent):
        tlp = (0, 0)
        dim = Commons.UIInstance.dim
        if parent is not None:
            tlp = parent.topleft()
            dim = parent.dimensions()
        return (
            int(dim[0] / 2) + self.xoffset + tlp[0],
            int(dim[1] / 2) + self.yoffset + tlp[1],
        )

    def topleft(self, dim, parent):
        anchor = self.anchor(parent)
        return (anchor[0] - int(dim[0] / 2), anchor[1] - int(dim[1] / 2))
