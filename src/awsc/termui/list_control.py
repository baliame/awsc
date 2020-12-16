from .control import Control
from .common import Commons
from .color import ColorBlack, ColorGold, ColorBlackOnGold, ColorBlackOnOrange, ColorWhite

class ListControl(Control):
  def __init__(self, parent, alignment, dimensions, color=ColorGold, selection_color=ColorBlackOnGold, title_color=ColorBlackOnOrange, *args, **kwargs):
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    self.entries = []
    self.hotkeys = {'KEY_DOWN': self.list_down, 'KEY_UP': self.list_up, 'KEY_PGUP': self.pageup, 'KEY_PGDOWN': self.pagedown, 'KEY_END': self.end, 'KEY_HOME': self.home}
    self.tooltips = {}
    self.color = color
    self.selection_color = selection_color
    self.title_color = title_color
    self.selected = 0
    self.column_titles = {"name": 30}
    self.column_order = ["name"]
    self.calculated = 0
    self._filter = None
    self.thread_share['clear'] = False
    self._cache = None
    self.thread_share['new_entries'] = []
    self.top = 0

  @property
  def filter(self):
    return self._filter

  @filter.setter
  def filter(self, value):
    sel = self.selection
    self._filter = value
    self.top = 0
    self.selected = 0
    self._cache = None

  def add_entry(self, entry):
    self.entries.append(entry)
    self._cache = None

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
    if inkey in self.hotkeys.keys():
      self.hotkeys[inkey](self)
      return True
    return False

  @property
  def filtered(self):
    if self._cache is None:
      self._cache = [e for e in self.entries if e.matches_filter(self._filter)]
    return self._cache

  def list_down(self, *args):
    if self.selected < len(self.filtered) - 1:
      self.selected += 1
    rows = self.rows
    if self.selected >= self.top + rows:
      self.top = max(0, self.selected - rows + 1)

  def list_up(self, *args):
    if self.selected > 0:
      self.selected -= 1
    if self.selected < self.top:
      self.top = self.selected

  def pagedown(self, *args):
    self.selected += self.rows
    self.selected = min(len(self.filtered), self.selected)
    rows = self.rows
    if self.selected >= self.top + rows:
      self.top = max(0, self.selected - rows + 1)

  def pageup(self, *args):
    self.selected -= self.rows
    self.selected = max(0, self.selected)
    if self.selected < self.top:
      self.top = self.selected

  def home(self, *args):
    self.selected = 0
    self.top = 0

  def end(self, *args):
    self.selected = len(self.filtered) - 1
    self.top = max(0, self.selected - self.rows + 1)

  @property
  def selection(self):
    if len(self.filtered) > self.selected:
      return self.filtered[self.selected]
    return None

  @property
  def rows(self):
    c = self.corners()
    y = c[1][0] + (0 if self.border is None else 1)
    y1 = c[1][1] - (0 if self.border is None else 1)
    return y1 - y

  def add_column(self, column, min_size=0, index=None):
    if index is None:
      self.column_order.append(column)
    else:
      self.column_order.insert(index, column)
    self.column_titles[column] = min_size
    self.calculated = 0

  def before_paint_critical(self):
    if self.thread_share['clear']:
      self.entries = []
      self.thread_share['clear'] = False
    if len(self.thread_share['new_entries']) > 0:
      self.entries.extend(self.thread_share['new_entries'])
      self._cache = None
      self.thread_share['new_entries'] = []

  def before_paint(self):
    super().before_paint()
    self.mutex.acquire()
    try:
      self.before_paint_critical()
    finally:
      self.mutex.release()
    self.sort()
    if self.selected >= len(self.entries):
      self.selected = len(self.entries) - 1
    if self.selected < 0:
      self.selected = 0

  def sort(self):
    pass

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
        if 'name' in self.column_titles:
          self.column_titles["name"] += rem
        else:
          self.column_titles[self.column_order[0]] += rem
      elif vals < win:
        diff = win - vals
        part = int(diff / len(self.column_titles))
        rem = diff - (part * len(self.column_titles))
        for k in self.column_titles.keys():
          self.column_titles[k] += part
        if 'name' in self.column_titles:
          self.column_titles["name"] += rem
        else:
          self.column_titles[self.column_order[0]] += rem
      self.calculated = win

    super().paint()
    c = self.corners()
    y = c[1][0] + (0 if self.border is None else 1)
    x = c[0][0] + (0 if self.border is None else 1)
    rows = self.rows
    for col in self.column_order:
      text = col
      m = self.column_titles[col]
      if len(col) > m:
        text = col[:m]
      elif len(col) < m:
        text = col + (int(m - len(col)) * ' ')
      Commons.UIInstance.print(text.upper(), xy=(x,y), color=self.title_color)
      x += m
    y += 1
    for i in range(self.top, min(len(self.filtered), self.top + rows)):
      item = self.filtered[i]
      x = c[0][0] + (0 if self.border is None else 1)
      for col in self.column_order:
        text = item.columns[col]
        m = self.column_titles[col]
        if len(text) > m:
          text = text[:m]
        elif len(text) < m:
          text = text + ((m - len(text)) * ' ')
        Commons.UIInstance.print(text, xy=(x,y), color=self.selection_color if i == self.selected else self.color)
        x += m
      y += 1

class ListEntry:
  def __init__(self, name, **kwargs):
    self.name = name
    self.columns = {"name" : name}
    self.columns.update({k:str(v) for (k, v) in kwargs.items()})
    self.controller_data = {}

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
