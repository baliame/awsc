from .common import Commons


class Block:
    def __init__(
        self, parent, alignment, dimensions, weight=0, tag="default", *args, **kwargs
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
        tl = self.alignment.topleft(self.dimensions, self.parent)
        return (tl[0] + self.dimensions[0], tl[1] + self.dimensions[1])

    @property
    def w(self):
        c = self.corners()
        return c[0][1] - c[0][0] + 1

    @property
    def h(self):
        c = self.corners()
        return c[1][1] - c[1][0] + 1

    @property
    def w_in(self):
        return self.w

    def corners(self):
        tl = self.topleft()
        br = (tl[0] + self.dimensions[0] - 1, tl[1] + self.dimensions[1] - 1)
        return ((tl[0], br[0]), (tl[1], br[1]))

    def before_paint(self):
        for block in reversed(self.blocks):
            block.before_paint()

    def paint(self):
        for block in reversed(self.blocks):
            block.paint()

    def add_block(self, block):
        Commons.UIInstance.dirty = True
        idx = 0
        for i in range(len(self.blocks)):
            blk = self.blocks[i]
            if blk.weight > block.weight:
                idx = i
                break
            i += 1
        block.parent = self
        self.blocks.insert(idx, block)

    def clear_blocks(self, tag=None):
        self.blocks = [
            block for block in self.blocks if tag is not None and block.tag != tag
        ]

    def remove_block(self, block):
        try:
            self.blocks.remove(block)
        except:
            pass

    def input(self, key):
        for block in self.blocks:
            if block.input(key):
                return True
        return False
