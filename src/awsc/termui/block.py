from .common import Commons


class Block:
    def __init__(
        self, parent, alignment, dimensions, *args, weight=0, tag="default", **kwargs
    ):
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
        self.parent.remove_block(self)
        self.parent.add_block(self)

    def topleft(self):
        return self.alignment.topleft(self.dimensions, self.parent)

    def bottomright(self):
        topleft = self.alignment.topleft(self.dimensions, self.parent)
        return (topleft[0] + self.dimensions[0], topleft[1] + self.dimensions[1])

    @property
    def width(self):
        corners = self.corners()
        return corners[0][1] - corners[0][0] + 1

    @property
    def height(self):
        corners = self.corners()
        return corners[1][1] - corners[1][0] + 1

    @property
    def w_in(self):
        return self.width

    def corners(self):
        topleft = self.topleft()
        botright = (
            topleft[0] + self.dimensions[0] - 1,
            topleft[1] + self.dimensions[1] - 1,
        )
        return ((topleft[0], botright[0]), (topleft[1], botright[1]))

    def before_paint(self):
        for block in reversed(self.blocks):
            block.before_paint()

    def paint(self):
        for block in reversed(self.blocks):
            block.paint()

    def add_block(self, block):
        Commons.UIInstance.dirty = True
        add_idx = 0
        for idx, existing_block in enumerate(self.blocks):
            if existing_block.weight > block.weight:
                add_idx = idx
                break
        block.parent = self
        self.blocks.insert(add_idx, block)

    def clear_blocks(self, tag=None):
        self.blocks = [
            block for block in self.blocks if tag is not None and block.tag != tag
        ]

    def remove_block(self, block):
        try:
            self.blocks.remove(block)
        except ValueError:
            pass

    def input(self, key):
        for block in self.blocks:
            if block.input(key):
                return True
        return False
