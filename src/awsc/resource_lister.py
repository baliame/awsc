import jq
from .common import Common, DefaultAnchor, DefaultDimension, DefaultBorder, SessionAwareDialog
from .termui.alignment import TopRightAnchor, Dimension
from .termui.dialog import DialogControl, DialogFieldLabel
from .termui.list_control import ListControl, ListEntry
from .termui.ui import ControlCodes
from .termui.text_browser import TextBrowser
from .info import HotkeyDisplay
import datetime
import json
import threading
import traceback
import sys
import pyperclip

def datetime_hack(x):
  if isinstance(x, datetime.datetime):
    return x.isoformat()
  raise TypeError("Unknown type")

class StopLoadingData(Exception):
  pass

class ResourceListerBase(ListControl):
  def __init__(self, *args, **kwargs):
    self.load_counter = 1
    self.closed = False
    if not hasattr(self, 'next_marker'):
      self.next_marker = None
    if not hasattr(self, 'next_marker_arg'):
      self.next_marker_arg = None
    super().__init__(*args, **kwargs)

  def on_close(self):
    self.closed = True

  def asynch(self, fn, clear=False, *args, **kwargs):
    try:
      t = threading.Thread(target=self.async_inner, args=args, kwargs={**kwargs, 'fn': fn, 'clear': clear}, daemon=True)
      t.start()
    except Exception as e:
      Common.Session.set_message('Failed to start AWS query thread.', Common.color('message_error'))

  def before_paint_critical(self):
    super().before_paint_critical()
    if 'thread_error' in self.thread_share:
      Common.Session.set_message(self.thread_share['thread_error'], Common.color('message_error'))
      del(self.thread_share['thread_error'])

  def async_inner(self, *args, fn, clear=False, **kwargs):
    try:
      self.mutex.acquire()
      try:
        if clear:
          self.thread_share['clear'] = True
      finally:
        self.mutex.release()

      for data in fn(*args, **kwargs):
        self.mutex.acquire()
        try:
          self.thread_share['new_entries'].extend(data)
        finally:
          self.mutex.release()
    except StopLoadingData as e:
      return
    except Exception as e:
      self.thread_share['thread_error'] = 'Refresh thread execution failed: {0}: {1}'.format(e.__class__.__name__, str(e))
      Common.Session.ui.log(str(e), 1)
      Common.Session.ui.log(traceback.format_exc(), 1)

  def get_data_generic(self, resource_key, list_method, list_kwargs, item_path, column_paths, hidden_columns, next_marker_name, next_marker_arg, *args):
    try:
      provider = Common.Session.service_provider(resource_key)
    except KeyError:
      return
    if callable(list_kwargs):
      list_kwargs = list_kwargs()
    next_marker = None
    ret = []
    while next_marker != '':
      if self.closed:
        raise StopLoadingData
      it_list_kwargs = list_kwargs.copy()
      if next_marker is not None and next_marker_arg is not None:
        it_list_kwargs[next_marker_arg] = next_marker
      response = getattr(provider, list_method)(**it_list_kwargs)

      it = jq.compile(item_path).input(text=json.dumps(response, default=datetime_hack)).first()
      if it is None:
        Common.Session.ui.log('get_data_generic for {0}.{1}({2}) returned None on path {3}'.format(resource_key, list_method, list_kwargs, item_path))
        Common.Session.ui.log('API response was:\n{0}'.format(json.dumps(response, default=datetime_hack)))
        return []

      for item in it:
        if self.closed:
          raise StopLoadingData
        init = {}
        for column, path in {**column_paths, **hidden_columns}.items():
          itree = item
          if callable(path):
            init[column] = path(item)
          else:
            try:
              init[column] = jq.compile(path).input(item).first()
            except StopIteration:
              init[column] = ''
        le = ListEntry(**init)
        le.controller_data = item
        if self.matches(le, *args):
          ret.append(le)
      if self.closed:
        raise StopLoadingData
      Common.Session.set_message('Loaded batch #{0}'.format(self.load_counter), Common.color('message_success'))
      yield ret
      if self.closed:
        raise StopLoadingData
      self.load_counter += 1
      if next_marker_name is not None and next_marker_name in response:
        next_marker = response[next_marker_name]
        ret = []
      else:
        next_marker = ''

  def matches(self, list_entry, *args):
    return True

  def tag_finder_generator(self, tagname, default='', taglist_key='Tags'):
    def fn(e, *args):
      if taglist_key in e:
        for tag in e[taglist_key]:
          if tag['Key'] == tagname:
            return tag['Value']
      return default
    return fn

  def empty(self, _):
    return ''

class ResourceLister(ResourceListerBase):
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

  def __init__(self, parent, alignment, dimensions, *args, selector_cb=None, **kwargs):
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
    if not hasattr(self, 'open_command') or self.open_command is None:
      self.open_command = None
    else:
      if not isinstance(self.open_command, str):
        if not hasattr(self, 'open_selection_arg'):
          raise AttributeError('open_command is defined but open_selection_arg is undefined')
      elif not hasattr(self, 'additional_commands') or self.open_command not in self.additional_commands:
        raise AttributeError('open_command refers to a key that is not in additional_commands')
    if not hasattr(self, 'item_path'):
      raise AttributeError('item_path is undefined')
    if not hasattr(self, 'hidden_columns'):
      self.hidden_columns = {}
    if not hasattr(self, 'column_paths'):
      raise AttributeError('column_paths is undefined')
    if 'name' not in self.column_paths and 'name' not in self.hidden_columns:
      raise AttributeError('name entry is required in column_paths or hidden_columns')
    if not hasattr(self, 'imported_column_sizes'):
      self.imported_column_sizes = {k: len(k) for k in self.column_paths.keys() if k != 'name'}
    if not hasattr(self, 'imported_column_order'):
      self.imported_column_order = sorted([k for k in self.column_paths.keys() if k != 'name'])
    if not hasattr(self, 'sort_column'):
      self.sort_column = 'name'
    if not hasattr(self, 'primary_key'):
      self.primary_key = 'name'

    self.selector_cb = selector_cb

    if self.open_command is not None:
      open_tooltip = 'Open'
      if isinstance(self.open_command, str):
        cmd = self.additional_commands[self.open_command]
        self.open_command = cmd['command']
        self.open_selection_arg = cmd['selection_arg']
        open_tooltip = cmd['tooltip']
      if selector_cb is None:
        self.add_hotkey('KEY_ENTER', self.open, open_tooltip)
      else:
        self.add_hotkey('o', self.open, open_tooltip)
    if self.describe_command is not None:
      self.add_hotkey('d', self.describe, 'Describe')
      if self.open_command is None and selector_cb is None:
        self.add_hotkey('KEY_ENTER', self.describe, 'Describe')
    if selector_cb is not None:
      self.add_hotkey('KEY_ENTER', self.select_and_close, 'Select')
    if hasattr(self, 'additional_commands'):
      for key, command_spec in self.additional_commands.items():
        self.add_hotkey(key, self.command_wrapper(command_spec['command'], command_spec['selection_arg']), command_spec['tooltip'])
    self.add_hotkey(ControlCodes.R, self.refresh_data, 'Refresh')
    if 'arn' in self.column_paths or 'arn' in self.hidden_columns:
      self.add_hotkey('r', self.copy_arn, 'Copy ARN')
    self.hotkey_display = HotkeyDisplay(self.parent, TopRightAnchor(1, 0), Dimension('33%|50', 8), self, session=Common.Session, highlight_color=Common.color('hotkey_display_title'), generic_color=Common.color('hotkey_display_value'))

    if 'name' in self.imported_column_sizes or 'name' in self.hidden_columns:
      self.column_titles = {}
    self.column_titles.update(self.imported_column_sizes)
    if 'name' in self.imported_column_order or 'name' in self.hidden_columns:
      self.column_order = []
    self.column_order.extend(self.imported_column_order)
    self.refresh_data()

  def copy_arn(self, *args):
    if self.selection is not None:
      pyperclip.copy(self.selection['arn'])
      Common.Session.set_message('Copied resource ARN to clipboard', Common.color('message_success'))

  def select_and_close(self):
    if self.selection is not None and self.selector_cb is not None and self.primary_key is not None:
      self.selector_cb(self.selection[self.primary_key])
      Common.Session.pop_frame()

  #def async_inner(self, *args, fn, clear=False, **kwargs):
    #try:
    #  data = fn(*args, **kwargs)
    #  self.mutex.acquire()
    #  try:
    #    if clear:
    #      self.thread_share['clear'] = True
    #    self.thread_share['new_entries'].extend(data)
    #  finally:
    #    self.mutex.release()
    #except Exception as e:
    #  self.thread_share['thread_error'] = 'Refresh thread execution failed: {0}: {1}'.format(e.__class__.__name__, str(e))
    #  Common.Session.ui.log(str(e), 1)
    #  Common.Session.ui.log(traceback.format_exc(), 1)

  def command(self, cmd, kw={}):
    if self.selection is not None:
      frame = cmd(**kw)
      if frame is not None:
        Common.Session.push_frame(frame)

  def command_wrapper(self, cmd, selection_arg):
    def fn(*args):
      self.command(cmd, {selection_arg: self.selection, 'pushed': True})
    return fn

  def describe(self, *args):
    if self.describe_command is not None:
      self.command_wrapper(self.describe_command, self.describe_selection_arg)()

  def open(self, *args):
    if self.open_command is not None:
      self.command_wrapper(self.open_command, self.open_selection_arg)()

  def get_data(self, *args, **kwargs):
    for y in self.get_data_generic(self.resource_key, self.list_method, self.list_kwargs, self.item_path, self.column_paths, self.hidden_columns, self.next_marker, self.next_marker_arg):
      yield y

  def refresh_data(self, *args, **kwargs):
    self.asynch(self.get_data, clear=True)

  def sort(self):
    self.entries.sort(key=lambda x: x.columns[self.sort_column])
    self._cache = None

class NoResults(Exception):
  pass

class MultiLister(ResourceListerBase):
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

  def __init__(self, parent, alignment, dimensions, compare_value, *args, compare_key='id', **kwargs):
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    self.add_column('type', 30, 0)
    self.add_column('id', 30, 1)
    if not hasattr(self, 'resource_descriptors'):
      raise AttributeError('resource_descriptors is undefined')
    if isinstance(compare_value, ListEntry):
      self.compare_value = compare_value[compare_key]
      self.orig_compare_value = compare_value
    else:
      self.compare_value = compare_value
      self.orig_compare_value = compare_value
    self.add_hotkey('KEY_ENTER', self.describe, 'Describe')
    self.add_hotkey('d', self.describe, 'Describe')
    self.add_hotkey(ControlCodes.R, self.refresh_data, 'Refresh')
    self.hotkey_display = HotkeyDisplay(self.parent, TopRightAnchor(1, 0), Dimension('33%|50', 8), self, session=Common.Session, highlight_color=Common.color('hotkey_display_title'), generic_color=Common.color('hotkey_display_value'))
    self.refresh_data()

  def describe(self, *args):
    if self.selection is not None:
      Common.Session.push_frame(GenericDescriber.opener(**{
        'describing': self.selection['id'],
        'content': json.dumps(self.selection.controller_data, sort_keys=True, indent=2),
        'pushed': True
      }))

  #def async_inner(self, *args, fn, clear=False, **kwargs):
  #  try:
  #    self.mutex.acquire()
  #    try:
  #      if clear:
  #        self.thread_share['clear'] = True
  #    finally:
  #      self.mutex.release()
  #
  #    for data in fn(*args, **kwargs):
  #      self.mutex.acquire()
  #      try:
  #        self.thread_share['new_entries'].extend(data)
  #      finally:
  #        self.mutex.release()
  #  except Exception as e:
  #    self.thread_share['thread_error'] = 'Refresh thread execution failed: {0}: {1}'.format(e.__class__.__name__, str(e))
  #    Common.Session.ui.log(str(e), 1)
  #    Common.Session.ui.log(traceback.format_exc(), 1)

  def get_data(self, *args, **kwargs):
    for elem in self.resource_descriptors:
      try:
        for y in self.get_data_generic(elem['resource_key'], elem['list_method'], elem['list_kwargs'], elem['item_path'], elem['column_paths'], elem['hidden_columns'], None, None, elem):
          yield y
      except NoResults:
        continue

  def matches(self, list_entry, elem, *args):
    raw_item = list_entry.controller_data
    if 'compare_as_list' not in elem or not elem['compare_as_list']:
      if callable(elem['compare_path']):
        val = elem['compare_path'](raw_item)
      else:
        try:
          val = jq.compile(elem['compare_path']).input(raw_item).first()
        except ValueError as e:
          return False
        except StopIteration as e:
          return False
      return val == self.compare_value
    else:
      if callable(elem['compare_path']):
        return self.compare_value in elem['compare_path'](raw_item)
      else:
        try:
          for val in jq.compile(elem['compare_path']).input(raw_item).first():
            if val == self.compare_value:
              return True
        except StopIteration as e:
          return False
    return False

  def refresh_data(self, *args, **kwargs):
    self.asynch(self.get_data, clear=True)

  def sort(self):
    self.entries.sort(key=lambda x: x.columns['type'])
    self._cache = None

class GenericDescriber(TextBrowser):
  prefix = 'generic_describer'
  title = 'Describe resource'

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
    return self.describing

  def __init__(self, parent, alignment, dimensions, describing, content, *args, **kwargs):
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    self.describing = describing
    self.add_text(content)
    self.hotkey_display = HotkeyDisplay(self.parent, TopRightAnchor(1, 0), Dimension('33%|50', 8), self, session=Common.Session, highlight_color=Common.color('hotkey_display_title'), generic_color=Common.color('hotkey_display_value'))

  def toggle_wrap(self, *args, **kwargs):
    super().toggle_wrap(*args, **kwargs)
    Common.Session.set_message('Text wrap {0}'.format('ON' if self.wrap else 'OFF'), Common.color('message_info'))

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

class DeleteResourceDialog(SessionAwareDialog):
  def __init__(self, parent, alignment, dimensions, *args, resource_type, resource_identifier, callback, **kwargs):
    kwargs['ok_action'] = self.accept_and_close
    kwargs['cancel_action'] = self.close
    kwargs['border'] = Border(Common.border('default'), Common.color('modal_dialog_border'), 'Delete Context', Common.color('modal_dialog_border_title'))
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    self.name = name
    self.add_field(DialogFieldLabel([
      ('Delete ', Common.color('modal_dialog_label')),
      (resource_type, Common.color('modal_dialog_label_highlight')),
      (' resource "', Common.color('modal_dialog_label')),
      (resource_identifier, Common.color('modal_dialog_label_highlight')),
      ('"?', Common.color('modal_dialog_label')),
    ]))
    self.add_field(DialogFieldLabel('This action cannot be undone.', Common.color('modal_dialog_error')))
    self.highlighted = 1
    self.callback = callback

  def input(self, inkey):
    if inkey.is_sequence and inkey.name == 'KEY_ESCAPE':
      self.close()
      return True
    return super().input(inkey)

  def accept_and_close(self):
    self.callback()
    self.close()
