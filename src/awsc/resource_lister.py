import jq
from .common import Common, DefaultAnchor, DefaultDimension, DefaultBorder
from .termui.alignment import TopRightAnchor, Dimension
from .termui.list_control import ListControl, ListEntry
from .termui.ui import ControlCodes
from .termui.text_browser import TextBrowser
from .info import HotkeyDisplay
import datetime
import json

def datetime_hack(x):
  if isinstance(x, datetime.datetime):
    return x.isoformat()
  raise TypeError("Unknown type")

class ResourceLister(ListControl):
  prefix = 'CHANGEME'
  title = 'CHANGEME'

  @classmethod
  def opener(cls, **kwargs):
    l = cls(
      Common.Session.ui.top_block,
      DefaultAnchor,
      DefaultDimension,
      weight=0,
      color=Common.color('{0}_generic'.format(cls.prefix), 'generic'),
      selection_color=Common.color('{0}_selection'.format(cls.prefix), 'selection'),
      title_color=Common.color('{0}_heading'.format(cls.prefix), 'column_title'),
      **kwargs
    )
    l.border=DefaultBorder(cls.prefix, cls.title, l.title_info())
    return [l, l.hotkey_display]

  def title_info(self):
    return None

  def __init__(self, parent, alignment, dimensions, *args, **kwargs):
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    if not hasattr(self, 'resource_key'):
      raise AttributeError('resource_key is undefined')
    if not hasattr(self, 'list_method'):
      raise AttributeError('list_method is undefined')
    if not hasattr(self, 'list_kwargs'):
      if 'list_kwargs' in kwargs:
        self.list_kwargs = kwargs['list_kwargs']
      else:
        self.list_kwargs = {}
    if not hasattr(self, 'describe_command'):
      self.describe_command = None
    else:
      if not hasattr(self, 'describe_selection_arg'):
        raise AttributeError('describe_command is defined but describe_selection_arg is undefined')
    if not hasattr(self, 'open_command'):
      self.open_command = None
    else:
      if not hasattr(self, 'open_selection_arg'):
        raise AttributeError('open_command is defined but open_selection_arg is undefined')
    if not hasattr(self, 'item_path'):
      raise AttributeError('item_path is undefined')
    if not hasattr(self, 'hidden_columns'):
      self.hidden_columns = {}
    if not hasattr(self, 'column_paths'):
      raise AttributeError('column_paths is undefined')
    if 'name' not in self.column_paths:
      raise AttributeError('name entry is required in column_paths')
    if not hasattr(self, 'imported_column_sizes'):
      self.imported_column_sizes = {k: len(k) for k in self.column_paths.keys() if k != 'name'}
    if not hasattr(self, 'imported_column_order'):
      self.imported_column_order = sorted([k for k in self.column_paths.keys() if k != 'name'])
    if not hasattr(self, 'sort_column'):
      self.sort_column = 'name'

    if self.open_command is not None:
      self.add_hotkey('KEY_ENTER', self.open, 'Open')
    if self.describe_command is not None:
      self.add_hotkey('d', self.describe, 'Describe')
      if self.open_command is None:
        self.add_hotkey('KEY_ENTER', self.describe, 'Describe')
    self.add_hotkey(ControlCodes.R, self.refresh_data, 'Refresh')
    self.hotkey_display = HotkeyDisplay(self.parent, TopRightAnchor(1, 0), Dimension('33%|50', 8), self, session=Common.Session, highlight_color=Common.color('hotkey_display_title'), generic_color=Common.color('hotkey_display_value'))

    if 'name' in self.imported_column_sizes:
      self.column_titles = {}
    self.column_titles.update(self.imported_column_sizes)
    if 'name' in self.imported_column_order:
      self.column_order = []
    self.column_order.extend(self.imported_column_order)
    self.refresh_data()

  def describe(self, *args):
    if self.describe_command is not None and self.selection is not None:
      Common.Session.push_frame(self.describe_command(**{self.describe_selection_arg: self.selection, 'pushed': True}))

  def open(self, *args):
    if self.open_command is not None and self.selection is not None:
      Common.Session.push_frame(self.open_command(**{self.open_selection_arg: self.selection, 'pushed': True}))

  def refresh_data(self, *args, **kwargs):
    try:
      provider = Common.Session.service_provider(self.resource_key)
    except KeyError:
      return
    response = getattr(provider, self.list_method)(**self.list_kwargs)
    self.entries = []

    for item in jq.compile(self.item_path).input(text=json.dumps(response, default=datetime_hack)).first():
      Common.Session.ui.log(str(item))
      init = {}
      for column, path in {**self.column_paths, **self.hidden_columns}.items():
        itree = item
        if callable(path):
          init[column] = path(item)
        else:
          init[column] = jq.compile(path).input(item).first()
      self.add_entry(ListEntry(**init))
    self.entries.sort(key=lambda x: x.columns[self.sort_column])
    if self.selected >= len(self.entries):
      self.selected = len(self.entries) - 1
    if self.selected < 0:
      self.selected = 0

class Describer(TextBrowser):
  prefix = 'CHANGEME'
  title = 'CHANGEME'

  @classmethod
  def opener(cls, **kwargs):
    l = cls(
      Common.Session.ui.top_block,
      DefaultAnchor,
      DefaultDimension,
      weight=0,
      color=Common.color('{0}_generic'.format(cls.prefix), 'generic'),
      filtered_color=Common.color('{0}_filtered'.format(cls.prefix), 'selection'),
      **kwargs,
    )
    l.border=DefaultBorder(cls.prefix, cls.title, l.title_info())
    return [l, l.hotkey_display]

  def title_info(self):
    return 'CHANGEME'

  def __init__(self, parent, alignment, dimensions, *args, **kwargs):
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    if not hasattr(self, 'resource_key'):
      raise AttributeError('resource_key is undefined')
    if not hasattr(self, 'describe_method'):
      raise AttributeError('describe_method is undefined')
    if not hasattr(self, 'describe_kwargs'):
      raise AttributeError('describe_kwargs is undefined')
    if not hasattr(self, 'object_path'):
      raise AttributeError('object_path is undefined')

    self.add_hotkey(ControlCodes.R, self.refresh_data, 'Refresh')
    self.hotkey_display = HotkeyDisplay(self.parent, TopRightAnchor(1, 0), Dimension('33%|50', 8), self, session=Common.Session, highlight_color=Common.color('hotkey_display_title'), generic_color=Common.color('hotkey_display_value'))

    self.refresh_data()

  def toggle_wrap(self, *args, **kwargs):
    super().toggle_wrap(*args, **kwargs)
    Common.Session.set_message('Text wrap {0}'.format('ON' if self.wrap else 'OFF'), Common.color('message_info'))

  def refresh_data(self, *args, **kwargs):
    try:
      provider = Common.Session.service_provider(self.resource_key)
    except KeyError:
      return
    response = getattr(provider, self.describe_method)(**self.describe_kwargs)
    self.clear()
    self.add_text(json.dumps(jq.compile(self.object_path).input(text=json.dumps(response, default=datetime_hack)).first(), sort_keys=True, indent=2))
