"""
This module defines classes for aligning blocks on the terminal.
"""
from .common import Commons


class Dimension:
    """
    Represents a width and height value.

    Upon each axis, the value can be specified in a few ways:
    * Directly, as a number of characters. (eg. 20)
    * As a percentage of space available in the current block. (eg. 100%)
    * As a difference of any amount of the above values (eg. 100%-5, 100%-20%, 5-2, 100%-2-1)
    * As the highest character count of any number of above operations (eg. 50%|60%-5|20)

    Attributes
    ----------
    width : str
        The width specification.
    height : str
        The height specification.
    """

    def __init__(self, width, height):
        """
        Initializes a Dimension object.

        Parameters
        ----------
        width : str
            The width specification.
        height : str
            The height specification.
        """
        self.width = width
        self.height = height

    def __getitem__(self, key):
        """
        Shorthand for retrieving the calculated width or height.

        Parameters
        ----------
        key : int|str
            One of 0, 1, "x", "y", "w" or "h".

        Returns
        -------
        int
            The evaluated width for keys 0, "x" or "w", otherwise, the evaluated height.
        """
        if key not in (0, 1, "x", "y", "w", "h"):
            raise KeyError("Bad dimension key " + key)
        val = self()
        return val[0] if key in (0, "x", "w") else val[1]

    @staticmethod
    def _v(value, space):
        """
        Evaluator function. Parses an axis specification and returns the character cell count.

        Parameters
        ----------
        value : str
            An axis specification.
        space : int
            The total space available on the axis.

        Returns
        -------
        int
            The resulting dimension.
        """
        if isinstance(value, str):
            test = value.split("|")
            if len(test) > 1:
                return max(Dimension._v(test_value, space) for test_value in test)
            test = value.split("-")
            if len(test) > 1:
                val = Dimension._v(test[0], space)
                for i in range(1, len(test)):
                    val -= Dimension._v(test[i], space)
                return val
            if value[-1] == "%":
                return int(space * float(value[:-1]) / 100) - 1
        return int(value)

    def __call__(self):
        """
        Evaluates the dimension into a width-height pair.

        Returns
        -------
        tuple(int, int)
            A tuple in the form of (width, height) as evaluated values.
        """
        dim = Commons.UIInstance.dim
        width = Dimension._v(self.width, dim[0])
        height = Dimension._v(self.height, dim[1])
        return (width, height)


class AbstractAnchor:
    """
    Anchor base class defining the interface anchors must implement.
    """

    def anchor(self, parent):
        """
        Returns the position of the anchor point of the block.

        Parameters
        ----------
        parent : awsc.termui.block.Block
            The parent block to anchor to. If None, the entire screen is considered the parent block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the anchor point.
        """
        return (0, 0)

    def topleft(self, dim, parent):
        """
        Returns the position of the top left corner of the anchored block.

        Parameters
        ----------
        dim : awsc.termui.alignment.Dimension
            The dimensions of the block being anchored.
        parent : awsc.termui.block.Block
            The parent block to anchor to. If None, the entire screen is considered the parent block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the top left corner of the block.
        """
        return (0, 0)


class TopLeftAnchor(AbstractAnchor):
    """
    Anchor class which specifies a block is aligned with the top-left corner of the parent at a fixed offset.

    Anchor point: top left corner of the block.

    Parent point: top left corner of the block.

    Attributes
    ----------
    top : int
        The vertical offset from the top left corner.
    left : int
        The horizontal offset from the top left corner.
    """

    def __init__(self, left, top):
        """
        Initializes a TopLeftAnchor object.

        Parameters
        ----------
        left : int
            The horizontal offset from the top left corner.
        top : int
            The vertical offset from the top left corner.
        """
        self.top = top
        self.left = left

    def anchor(self, parent):
        """
        Returns the position of the anchor point of the block.

        Parameters
        ----------
        parent : awsc.termui.block.Block
            The parent block to anchor to. If None, the entire screen is considered the parent block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the anchor point (top left corner).
        """
        if parent is None:
            return (self.left, self.top)
        tlp = parent.topleft()
        return (tlp[0] + self.left, tlp[1] + self.top)

    def topleft(self, dim, parent):
        """
        Returns the position of the top left corner of the anchored block.

        Parameters
        ----------
        dim : awsc.termui.alignment.Dimension
            The dimensions of the block being anchored.
        parent : awsc.termui.block.Block
            The parent block to anchor to. If None, the entire screen is considered the parent block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the top left corner of the block.
        """
        return self.anchor(parent)


class BottomLeftAnchor(AbstractAnchor):
    """
    Anchor class which specifies a block is aligned with the bottom-left corner of the parent at a fixed offset.

    Anchor point: bottom left corner of the block.

    Parent point: bottom left corner of the block.

    Attributes
    ----------
    bottom : int
        The vertical offset from the bottom left corner.
    left : int
        The horizontal offset from the bottom left corner.
    """

    def __init__(self, left, bottom):
        """
        Initializes a BottomLeftAnchor object.

        Parameters
        ----------
        left : int
            The horizontal offset from the bottom left corner.
        bottom : int
            The vertical offset from the bottom left corner.
        """
        self.bottom = bottom
        self.left = left

    def anchor(self, parent):
        """
        Returns the position of the anchor point of the block.

        Parameters
        ----------
        parent : awsc.termui.block.Block
            The parent block to anchor to. If None, the entire screen is considered the parent block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the anchor point (bottom left corner).
        """
        if parent is None:
            return (self.left, self.bottom)
        tlp = parent.topleft()
        brp = parent.bottomright()
        return (tlp[0] + self.left, brp[1] - self.bottom)

    def topleft(self, dim, parent):
        """
        Returns the position of the top left corner of the anchored block.

        Parameters
        ----------
        dim : awsc.termui.alignment.Dimension
            The dimensions of the block being anchored.
        parent : awsc.termui.block.Block
            The parent block to anchor to. If None, the entire screen is considered the parent block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the top left corner of the block.
        """
        anchor = self.anchor(parent)
        return (anchor[0], anchor[1] - dim[1] + 1)


class TopRightAnchor(AbstractAnchor):
    """
    Anchor class which specifies a block is aligned with the top-right corner of the parent at a fixed offset.

    Anchor point: top right corner of the block.

    Parent point: top right corner of the block.

    Attributes
    ----------
    top : int
        The vertical offset from the top right corner.
    right : int
        The horizontal offset from the top right corner.
    """

    def __init__(self, right, top):
        """
        Initializes a TopRightAnchor object.

        Parameters
        ----------
        right : int
            The horizontal offset from the top right corner.
        top : int
            The vertical offset from the top right corner.
        """
        self.top = top
        self.right = right

    def anchor(self, parent):
        """
        Returns the position of the anchor point of the block.

        Parameters
        ----------
        parent : awsc.termui.block.Block
            The parent block to anchor to. If None, the entire screen is considered the parent block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the anchor point (top right corner).
        """
        if parent is None:
            return (self.right, self.top)
        tlp = parent.topleft()
        brp = parent.bottomright()
        return (brp[0] - self.right, tlp[1] + self.top)

    def topleft(self, dim, parent):
        """
        Returns the position of the top left corner of the anchored block.

        Parameters
        ----------
        dim : awsc.termui.alignment.Dimension
            The dimensions of the block being anchored.
        parent : awsc.termui.block.Block
            The parent block to anchor to. If None, the entire screen is considered the parent block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the top left corner of the block.
        """
        anchor = self.anchor(parent)
        return (anchor[0] - dim[0] + 1, anchor[1])


class CenterAnchor(AbstractAnchor):
    """
    Anchor class which specifies a block is aligned with the center of the parent at a fixed offset.

    Anchor point: center of the block.

    Parent point: center of the block.

    Attributes
    ----------
    xoffset : int
        The horizontal offset from the center.
    yoffset : int
        The vertical offset from the center
    """

    def __init__(self, xoffset, yoffset):
        """
        Initializes a CenterAnchor object.

        Parameters
        ----------
        xoffset : int
            The horizontal offset from the center.
        yoffset : int
            The vertical offset from the center
        """
        self.xoffset = xoffset
        self.yoffset = yoffset

    def anchor(self, parent):
        """
        Returns the position of the anchor point of the block.

        Parameters
        ----------
        parent : awsc.termui.block.Block
            The parent block to anchor to. If None, the entire screen is considered the parent block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the anchor point (center).
        """
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
        """
        Returns the position of the top left corner of the anchored block.

        Parameters
        ----------
        dim : awsc.termui.alignment.Dimension
            The dimensions of the block being anchored.
        parent : awsc.termui.block.Block
            The parent block to anchor to. If None, the entire screen is considered the parent block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the top left corner of the block.
        """
        anchor = self.anchor(parent)
        return (anchor[0] - int(dim[0] / 2), anchor[1] - int(dim[1] / 2))
