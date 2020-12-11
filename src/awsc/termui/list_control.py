from .control import Control
from .common import Commons
from .color import ColorBlack, ColorGold, ColorBlackOnGold, ColorBlackOnOrange, ColorWhite

class ListControl(Control):
  def __init__(self, parent, alignment, dimensions, color=ColorGold, selection_color=ColorBlackOnGold, title_color=ColorBlackOnOrange, *args, **kwargs):
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    self.entries = []
    self.hotkeys = {'KEY_DOWN': self.list_down, 'KEY_UP': self.list_up}
    self.tooltips = {}
    self.color = color
    self.selection_color = selection_color
    self.title_color = title_color
    self.selected = 0
    self.column_titles = {"name": 30}
    self.column_order = ["name"]
    self.calculated = 0
    self._filter = None

  @property
  def filter(self):
    return self._filter

  @filter.setter
  def filter(self, value):
    sel = self.selection
    self._filter = value
    unf = len([entry for entry in self.entries if entry.matches_filter(self._filter)])
    if self.selected >= unf:
      self.selected = unf - 1 if unf > 0 else 0

  def add_entry(self, entry):
    self.entries.append(entry)

  def add_hotkey(self, hotkey, action, tooltip=None):
    self.hotkeys[hotkey] = action
    if tooltip is not None:
      self.tooltips[hotkey] = tooltip

  def input(self, key):
    inkey = str(key)
    if key.is_sequence:
      inkey = key.name
    else:
      inkey = inkey.lower()
    Commons.UIInstance.log('ListControl inkey: {0}'.format(inkey))
    if inkey in self.hotkeys.keys():
      self.hotkeys[inkey](self)
      return True
    return False

  def list_down(self, *args):
    if self.selected < len(self.entries) - 1:
      self.selected += 1

  def list_up(self, *args):
    if self.selected > 0:
      self.selected -= 1

  @property
  def selection(self):
    if len(self.entries) > self.selected:
      return self.entries[self.selected]
    return None

  def add_column(self, column, min_size=0, index=None):
    if index is None:
      self.column_order.append(column)
    else:
      self.column_order.insert(index, column)
    self.column_titles[column] = min_size
    self.calculated = 0

  def paint(self):
    Commons.UIInstance.log('Painting ListControl', level=2)
    win = self.w_in
    if win != self.calculated:
      vals = 0
      for k, v in self.column_titles.items():
        vals += v
      if vals > win:
        ratio = float(vals) / float(win)
        tot = 0
        for k in self.column_titles.keys():
          self.column_titles[k] = int(float(self.column_titles[k]) / ratio)
          tot += self.column_titles[k]
        rem = win - tot
        self.column_titles["name"] += rem
      elif vals < win:
        diff = win - vals
        part = int(diff / len(self.column_titles))
        rem = diff - (part * len(self.column_titles))
        for k in self.column_titles.keys():
          self.column_titles[k] += part
        self.column_titles["name"] += rem
      self.calculated = win

    super().paint()
    c = self.corners()
    y = c[1][0] + (0 if self.border is None else 1)
    x = c[0][0] + (0 if self.border is None else 1)
    for col in self.column_order:
      text = col
      m = self.column_titles[col]
      if len(col) > m:
        text = col[:m]
      elif len(col) < m:
        text = col + (int(m - len(col)) * ' ')
      Commons.UIInstance.print(text.upper(), xy=(x,y), color=self.title_color)
      x += m
    idx = 0
    y += 1
    for item in self.entries:
      if not item.matches_filter(self.filter):
        continue
      x = c[0][0] + (0 if self.border is None else 1)
      for col in self.column_order:
        text = item.columns[col]
        m = self.column_titles[col]
        if len(text) > m:
          text = text[:m]
        elif len(text) < m:
          text = text + ((m - len(text)) * ' ')
        Commons.UIInstance.print(text, xy=(x,y), color=self.selection_color if idx == self.selected else self.color)
        x += m
      idx += 1
      y += 1

class ListEntry:
  def __init__(self, name, **kwargs):
    self.name = name
    self.columns = {"name" : name}
    self.columns.update({k:str(v) for (k, v) in kwargs.items()})

  def __getitem__(self, item):
    return self.columns[item]

  def matches_filter(self, filter):
    if filter is None:
      return True
    f = filter.lower()
    for k, column in self.columns.items():
      if f in column.lower():
        return True
    return False
