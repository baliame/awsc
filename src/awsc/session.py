from .info import InfoDisplay, NeutralDialog, HotkeyDisplay
from .termui.ui import UI, ControlCodes
from .termui.dialog import DialogFieldLabel, DialogControl
from .termui.alignment import TopLeftAnchor, BottomLeftAnchor, Dimension
import time
import subprocess
import tempfile
import os
import jq

class Session:
  def jq(self, stmt):
    if stmt not in self.jqc:
      self.jqc[stmt] = jq.compile(stmt)
    return self.jqc[stmt]

  def __init__(self, config, highlight_color, generic_color):
    self.jqc = {}
    self.ui = UI()
    self.config = config
    self.context_update_hooks = []
    self.info_display = InfoDisplay(
      self.ui.top_block,
      TopLeftAnchor(1, 0),
      Dimension('50%', 8),
      highlight_color=highlight_color,
      generic_color=generic_color,
      info=['Context', 'Region', 'UserId', 'Account', 'SSH Key', 'Default SSH username'],
      weight=-10
    )
    self.global_hotkey_tooltips = {':': 'Command palette', '/': 'Filter / search', ControlCodes.C: 'Exit'}
    self.message_display = NeutralDialog(
      self.ui.top_block,
      BottomLeftAnchor(0, 0),
      Dimension('100%', 3),
      confirm_text = None,
      cancel_text = None,
      color=generic_color,
      weight=-10,
    )
    self._message_label = DialogFieldLabel('')
    self.message_display.add_field(self._message_label)
    self._context = None
    self.context = config['default_context']
    self.region = config['default_region']
    self.ssh_key = config['default_ssh_key']
    self.stack = []
    self.stack_frame = []
    self.resource_main = None
    self.service_provider = None
    self.message_time = 0
    self.last_tick = time.time()
    self.ui.tickers.append(self.tick)

    self.filterer = None
    self.commander = None
    self.commander_options = {}

  def set_message(self, text, color):
    self._message_label.texts = [(text, color)]
    self.message_time = 5.0
    self.last_tick = time.time()
    self.ui.dirty = True

  def replace_frame(self, new_frame, drop_stack=True):
    for elem in self.stack_frame:
      elem.parent.remove_block(elem)
    if drop_stack:
      self.stack = []
    self.resource_main = new_frame[0]
    self.stack_frame = new_frame[:]
    self.ui.dirty = True

  def push_frame(self, new_frame):
    self.stack.append(self.stack_frame[:])
    self.replace_frame(new_frame, drop_stack=False)
    if hasattr(new_frame[0], 'add_hotkey'):
      if 'KEY_ESCAPE' not in new_frame[0].tooltips:
        new_frame[0].add_hotkey('KEY_ESCAPE', self.pop_frame, 'Back')
    self.ui.dirty = True

  def pop_frame(self, *args):
    for elem in self.stack_frame:
      if hasattr(elem, 'on_close'):
        elem.on_close()
    if len(self.stack) > 0:
      self.replace_frame(self.stack.pop(), drop_stack=False)
    for elem in self.stack_frame:
      elem.reparent()
    self.ui.dirty = True

  def extend_frame(self, control):
    self.stack_frame.append(control)
    self.ui.dirty = True

  def remove_from_frame(self, control):
    if hasattr(control, 'on_close'):
      control.on_close()
    self.stack_frame.remove(control)
    self.ui.dirty = True

  def tick(self):
    delta = time.time() - self.last_tick
    self.last_tick += delta
    if self.message_time > 0:
      self.message_time -= delta
      if self.message_time <= 0:
        self._message_label.texts = []
    if hasattr(self.resource_main, 'auto_refresh'):
      self.resource_main.auto_refresh()

  @property
  def context(self):
    return self._context

  @context.setter
  def context(self, value):
    if self._context == value:
      return
    self._context = value
    self.info_display['Context'] = value
    for elem in self.context_update_hooks:
      elem()

  @property
  def region(self):
    return self._region

  @region.setter
  def region(self, value):
    self._region = value
    self.info_display['Region'] = value

  @property
  def ssh_key(self):
    return self._ssh_key

  @ssh_key.setter
  def ssh_key(self, value):
    self._ssh_key = value
    self.info_display['SSH Key'] = value
    self.info_display['Default SSH username'] = self.config['default_ssh_usernames'][value] if value in self.config['default_ssh_usernames'] else ''

  def get_keypair_association(self, keypair_id):
    if keypair_id in self.config['keypair_associations']:
      return self.config['keypair_associations'][keypair_id]
    return ''

  def set_keypair_association(self, keypair_id, key_name):
    self.config['keypair_associations'][keypair_id] = key_name
    self.config.write_config()

  def textedit(self, value):
    editor = self.config['editor_command']
    temp = tempfile.NamedTemporaryFile('w', delete=False)
    tf = temp.name
    try:
      temp.write(value)
      temp.close()
      self.ui.unraw(subprocess.run, ['bash', '-c', editor.format(tf)])
      with open(tf, 'r') as temp:
        return temp.read()
    finally:
      os.unlink(temp.name)
