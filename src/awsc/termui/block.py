from .common import Commons
from .alignment import TopLeftAnchor, Dimension

class Block:
  def __init__(self, parent, alignment, dimensions, weight = 0, tag='default', *args, **kwargs):
    Commons.UIInstance.log('Initializing Block', level=2)
    self.blocks = []
    self.weight = weight
    if parent is not None:
      parent.add_block(self)
    self.parent = parent
    self.alignment = alignment
    self.dimensions = dimensions
    self.tag = tag

  def reparent(self):
    self.parent.remove_block(self)
    self.parent.add_block(self)

  def topleft(self):
    return self.alignment.topleft(self.dimensions, self.parent)

  def bottomright(self):
    tl = self.alignment.topleft(self.dimensions, self.parent)
    return (tl[0]+self.dimensions[0], tl[1]+self.dimensions[1])

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
    br = (tl[0]+self.dimensions[0] - 1, tl[1]+self.dimensions[1] - 1)
    return ((tl[0], br[0]), (tl[1], br[1]))

  def paint(self):
    Commons.UIInstance.log('Painting Block {0}'.format(self), level=2)
    Commons.UIInstance.log(str(self.blocks), level=3)
    for block in reversed(self.blocks):
      block.paint()

  def add_block(self, block):
    Commons.UIInstance.log('Adding Block to {0}'.format(self), level=2)
    idx = 0
    for i in range(len(self.blocks)):
      blk = self.blocks[i]
      if blk.weight > block.weight:
        idx = i
        break
      i += 1
    block.parent = self
    self.blocks.insert(idx, block)
    Commons.UIInstance.log(str(self.blocks), level=3)

  def clear_blocks(self, tag=None):
    self.blocks = [block for block in self.blocks if tag is not None and block.tag != tag]

  def remove_block(self, block):
    try:
      self.blocks.remove(block)
    except:
      pass

  def input(self, key):
    if self.parent is None:
      Commons.UIInstance.log(str(key) if not key.is_sequence else str((str(key), key.name, key.code)))
    for block in self.blocks:
      if block.input(key):
        return True
    return False