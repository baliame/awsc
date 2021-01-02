from .control import Control
from .common import Commons
from .color import ColorBlack, ColorGold, ColorBlackOnGold, ColorBlackOnOrange, ColorWhite
import pyperclip

class TextBrowser(Control):
  def __init__(self, parent, alignment, dimensions, color=ColorGold, filtered_color=ColorBlackOnOrange, *args, **kwargs):
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    self.entries = []
    self.hotkeys = {
      'KEY_DOWN': self.scroll_down,
      'KEY_UP': self.scroll_up,
      'KEY_LEFT': self.scroll_left,
      'KEY_RIGHT': self.scroll_right,
      'c': self.copy_contents,
      'w': self.toggle_wrap,
      'KEY_END': self.end,
      'KEY_HOME': self.home,
      'KEY_PGUP': self.pgup,
      'KEY_PGDOWN': self.pgdown,
    }
    self.tooltips = {'c': 'Copy', 'w': 'Toggle Wrap'}
    self.color = color
    self.filtered_color = filtered_color
    self.lines = []
    self._prefilter_lines = []
    self.top = 0
    self.left = 0
    self._filter_line = 0
    self.wrap = False
    self._filter = None
    self._current_filter_match = []

  def _raw(self, line_part):
    if isinstance(line_part, tuple):
      return line_part[0]
    return line_part

  def rawlines(self):
    return [self.raw(i) for i in range(len(self.lines))]

  def raw(self, line=None):
    if line is None:
      return '\n'.join(self.rawlines())
    else:
      return ''.join([self._raw(self.lines[line][i]) for i in range(len(self.lines[line]))])

  def add_text(self, text):
    add = [[a] for a in text.split('\n')]
    self.lines.extend(add)
    self._prefilter_lines.extend(add)
    Commons.UIInstance.dirty = True

  def clear(self):
    Commons.UIInstance.dirty = True
    self.lines = []
    self._prefilter_lines = []
    self.filter = None
    self.top = 0
    self.left = 0

  @property
  def filter(self):
    return self._filter

  @filter.setter
  def filter(self, value):
    Commons.UIInstance.dirty = True
    refilter = False
    if self._filter != value:
      self._filter_line = -1
      self.lines = self._prefilter_lines[:]
      self._current_filter_match = []
      refilter = True

    self._filter = value

    if value is None or value == '':
      return

    if refilter:
      for i in range(len(self.lines)):
        rawline = self.raw(i)
        ml = rawline.split(self._filter)
        self.lines[i] = [ml[0]]
        for j in range(1, len(ml)):
          self.lines[i].append((self._filter, self.filtered_color))
          self.lines[i].append(ml[j])
        if len(ml) > 1:
          self._current_filter_match.append(i)

    for elem in self._current_filter_match:
      if elem > self._filter_line:
        self._filter_line = elem
        self.top = elem
        return
    if len(self._current_filter_match) > 0:
      self.top = self._current_filter_match[0]
      self._filter_line = self.top

  def add_hotkey(self, hotkey, action, tooltip=None):
    self.hotkeys[hotkey] = action
    if tooltip is not None:
      self.tooltips[hotkey] = tooltip
    Commons.UIInstance.dirty = True

  def input(self, key):
    inkey = str(key)
    if key.is_sequence:
      inkey = key.name
    else:
      inkey = inkey.lower()
    if inkey in self.hotkeys.keys():
      self.hotkeys[inkey](self)
      Commons.UIInstance.dirty = True
      return True
    return False

  def toggle_wrap(self, *args):
    self.wrap = not self.wrap
    if self.wrap:
      self.left = 0

  def scroll_down(self, *args):
    if self.top < len(self.lines) - 1:
      self.top += 1

  def scroll_up(self, *args):
    if self.top > 0:
      self.top -= 1

  def scroll_right(self, *args):
    if self.wrap:
      return
    self.left += 1

  def scroll_left(self, *args):
    if self.wrap:
      return
    if self.left > 0:
      self.left -= 1

  def end(self, *args):
    c = self.corners()
    y0 = c[1][0] + (0 if self.border is None else 1)
    y1 = c[1][1] - (0 if self.border is None else 1)
    h = y1 - y0 + 1
    limit = len(self.lines) - h if not self.wrap else len(self.lines) - 1
    self.top = max(limit, 0)

  def home(self, *args):
    self.top = 0

  def pgup(self, *args):
    c = self.corners()
    y0 = c[1][0] + (0 if self.border is None else 1)
    y1 = c[1][1] - (0 if self.border is None else 1)
    h = y1 - y0 + 1
    self.top = max(self.top - h, 0)

  def pgdown(self, *args):
    c = self.corners()
    y0 = c[1][0] + (0 if self.border is None else 1)
    y1 = c[1][1] - (0 if self.border is None else 1)
    h = y1 - y0 + 1
    limit = len(self.lines) - h if not self.wrap else len(self.lines) - 1
    self.top = max(min(limit, self.top + h), 0)

  def copy_contents(self, *args):
    pyperclip.copy(self.raw())

  def paint(self):
    super().paint()
    c = self.corners()
    y = c[1][0] + (0 if self.border is None else 1)
    y1 = c[1][1] - (0 if self.border is None else 1)
    x0 = c[0][0] + (0 if self.border is None else 1)
    x1 = c[0][1] - (0 if self.border is None else 1)
    for i in range(self.top, len(self.lines)):
      line = self.lines[i]
      skip_chars = self.left
      x = x0
      end = False
      for elem in line:
        buf = self._raw(elem)
        if skip_chars > len(buf):
          skip_chars -= len(buf)
          continue
        elif skip_chars > 0:
          buf = buf[skip_chars:]
          skip_chars = 0
        color = self.color if not isinstance(elem, tuple) else elem[1]

        while len(buf) > 0:
          space = x1 - x + 1
          text = buf[:space]
          buf = buf[space:]
          Commons.UIInstance.print(text, xy=(x, y), color=color)
          x += len(text)
          if x > x1:
            y += 1
            x = x0
            if not self.wrap:
              end = True

          if end or y > y1:
            break
      if not end:
        y += 1
        x = x0
      if y > y1:
        break




