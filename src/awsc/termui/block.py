"""
This module defines blocks that allow segmenting the terminal screen.
"""
from .common import Commons


class Block:
    """
    A Block object represents a section of the screen. A Block may contain additional Blocks or act as a control.

    Attributes
    ----------
    blocks : list
        A set of child Block objects.
    weight : int
        Sibling blocks are drawn in order from highest weight to lowest weight.
    parent : awsc.termui.block.Block
        The parent Block object. None indicates that the parent is the entire screen.
    alignment : awsc.termui.alignment.AbstractAnchor
        The anchor specifier for this Block within the parent Block.
    dimensions : awsc.termui.alignment.Dimension
        The size specifier for this Block.
    tag : str
        Tags allow grouping sibling Blocks, and removing them together.
    """

    def __init__(
        self, parent, alignment, dimensions, *args, weight=0, tag="default", **kwargs
    ):
        """
        Initializes a Block object.

        Parameters
        ----------
        parent : awsc.termui.block.Block
            The parent Block object. None indicates that the parent is the entire screen.
        alignment : awsc.termui.alignment.AbstractAnchor
            The anchor specifier for this Block within the parent Block.
        dimensions : awsc.termui.alignment.Dimension
            The size specifier for this Block.
        weight : int
            Sibling blocks are drawn in order from highest weight to lowest weight.
        tag : str
            Tags allow grouping sibling Blocks, and removing them together.
        """
        self.blocks = []
        self.weight = weight
        if parent is not None:
            parent.add_block(self)
        self.parent = parent
        self.alignment = alignment
        self.dimensions = dimensions
        self.tag = tag
        Commons.UIInstance.dirty = True

    def reparent(self):
        """
        Shorthand function for removing a Block from its parent and re-adding it.

        Useful for reordering sibling Blocks with equal weight, as reparenting will send the block atop all other sibling blocks with equal weight.

        Reparenting is also required if the weight of the block changes, as blocks are only sorted upon insertion.
        """
        self.parent.remove_block(self)
        self.parent.add_block(self)

    def topleft(self):
        """
        Returns the coordinates of the top left corner of the block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the top left corner of the block.
        """
        return self.alignment.topleft(self.dimensions, self.parent)

    def bottomright(self):
        """
        Returns the coordinates of the bottom right corner of the block.

        Returns
        -------
        tuple(int, int)
            The (x, y) coordinates of the bottom right corner of the block.
        """
        topleft = self.alignment.topleft(self.dimensions, self.parent)
        return (topleft[0] + self.dimensions[0], topleft[1] + self.dimensions[1])

    @property
    def width(self):
        """
        Read-only property for the width of the block.

        Returns
        -------
        int
            The width of the block in character cells.
        """
        corners = self.corners
        return corners[0][1] - corners[0][0] + 1

    @property
    def height(self):
        """
        Read-only property for the height of the block.

        Returns
        -------
        int
            The height of the block in character cells.
        """
        corners = self.corners
        return corners[1][1] - corners[1][0] + 1

    @property
    def w_in(self):
        """
        Read-only property for the inner width of the block. Subclasses may implement features which take away from the "usable" space
        of a block, therefore affecting its inner width without affecting its total width.

        Returns
        -------
        int
            The inner width of the block in character cells.
        """
        return self.width

    @property
    def corners(self):
        """
        Read-only property for calculating the four corners of the block.

        Returns
        -------
        tuple(tuple(int, int), tuple(int, int))
            Contains the horizontal bounds and vertical bounds of the block in the form of ((x0, x1), (y0, y1)) in character cell coordinates.
        """
        topleft = self.topleft()
        botright = (
            topleft[0] + self.dimensions[0] - 1,
            topleft[1] + self.dimensions[1] - 1,
        )
        return ((topleft[0], botright[0]), (topleft[1], botright[1]))

    @property
    def inner(self):
        """
        Read-only property for calculating the four inner corners of the block. Subclasses may implement features which take away from
        the "usable" space of a block, therefore affecting its inner corner coordinates without affecting its corners.

        Returns
        -------
        tuple(tuple(int, int), tuple(int, int))
            Contains the horizontal bounds and vertical inner corners of the block in the form of ((x0, x1), (y0, y1)) in character cell
            coordinates.
        """
        return self.corners

    def before_paint(self):
        """
        Hook function for acting on the block before any blocks are painted for the current frame.
        """
        for block in reversed(self.blocks):
            block.before_paint()

    def paint(self):
        """
        Hook function for painting the block. The block is expected to handle its own output through interacting with the UI object.
        """
        for block in reversed(self.blocks):
            block.paint()

    def add_block(self, block):
        """
        Adds a new child block to this block.

        When a new block is inserted, it is added as the topmost block for its own weight.

        Parameters
        ----------
        block : awsc.termui.block.Block
            The child block to insert.
        """
        Commons.UIInstance.dirty = True
        add_idx = 0
        for idx, existing_block in enumerate(self.blocks):
            if existing_block.weight > block.weight:
                add_idx = idx
                break
        block.parent = self
        self.blocks.insert(add_idx, block)

    def clear_blocks(self, tag=None):
        """
        Removes all blocks with the matching tag from the child blocks of this block.

        If no tag is provided, this function clears all child blocks.

        Parameters
        ----------
        tag : str
            The tag to search for when clearing blocks.
        """
        self.blocks = [
            block for block in self.blocks if tag is not None and block.tag != tag
        ]

    def remove_block(self, block):
        """
        Removes a specific block from this block.

        Parameters
        ----------
        block : awsc.termui.block.Block
            The block to remove from the children of this block.
        """
        try:
            self.blocks.remove(block)
        except ValueError:
            pass

    def input(self, key):
        """
        Input handler hook function. The function's return value indicates whether the processing of the input has been done
        by this or a child block and no further processing of the input should take place.

        The input will be piped to the lowest weight block first, proceeding in order to the highest weight block until a block
        reports that it handled the input successfully.

        Any block has the option of reacting to an input but not marking it as handled. This may be useful for key press debugging
        blocks.

        Not all keys have to be handled by the same block. A set of keys may be isolated as unhandled by any block other than a global
        hotkey handler block if needed.

        Parameters
        ----------
        key : blessed.keyboard.Keystroke
            The raw inkey() from the keyboard event.

        Returns
        -------
        bool
            True if the input was handled by this or any other child block, False otherwise.
        """
        for block in self.blocks:
            if block.input(key):
                return True
        return False
