import re
from .common import Common
from .termui.alignment import TopLeftAnchor, TopRightAnchor, CenterAnchor, Dimension
from .termui.dialog import DialogControl, DialogFieldLabel, DialogFieldText
from .termui.list_control import ListControl, ListEntry
from .termui.common import Commons
from .termui.control import Control, Border
from .info import HotkeyDisplay
from botocore import exceptions

class DeleteContextDialog(DialogControl):
  def __init__(self, parent, alignment, dimensions, name='', caller=None, *args, **kwargs):
    kwargs['ok_action'] = self.accept_and_close
    kwargs['cancel_action'] = self.close
    kwargs['border'] = Border(Common.border('default'), Common.color('modal_dialog_border'), 'Delete Context', Common.color('modal_dialog_border_title'))
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    self.name = name
    self.add_field(DialogFieldLabel([('Delete context "', Common.color('modal_dialog_label')), (name, Common.color('modal_dialog_label_highlight')), ('"?', Common.color('modal_dialog_label'))]))
    self.highlighted = 1
    self.caller = caller

  def input(self, inkey):
    if inkey.is_sequence and inkey.name == 'KEY_ESCAPE':
      self.close()
      return True
    return super().input(inkey)

  def accept_and_close(self):
    Common.Configuration.delete_context(self.name)
    self.close()

  def close(self):
    if self.caller is not None:
      self.caller.reload_contexts()
    self.parent.remove_block(self)

class AddContextDialog(DialogControl):
  def __init__(self, parent, alignment, dimensions, caller=None, *args, **kwargs):
    self.accepts_inputs = True
    kwargs['border'] = Border(Common.border('default'), Common.color('modal_dialog_border'), 'New Context', Common.color('modal_dialog_border_title'))
    kwargs['ok_action'] = self.accept_and_close
    kwargs['cancel_action'] = self.close
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    self.add_field(DialogFieldLabel('Enter AWS context details'))
    self.error_label = DialogFieldLabel('', default_color=Common.color('modal_dialog_error'))
    self.add_field(self.error_label)
    self.add_field(DialogFieldLabel(''))
    self.name_field = DialogFieldText('Name:', label_min=16)
    self.add_field(self.name_field)
    self.account_field = DialogFieldText('Account number:', label_min=16)
    self.add_field(self.account_field)
    self.access_key_field = DialogFieldText('Access key:', label_min=16)
    self.add_field(self.access_key_field)
    self.secret_key_field = DialogFieldText('Secret key:', label_min=16)
    self.add_field(self.secret_key_field)
    self.caller = caller

  def input(self, inkey):
    if not self.accepts_inputs:
      return True
    if inkey.is_sequence and inkey.name == 'KEY_ESCAPE':
      self.close()
      return True
    return super().input(inkey)

  def accept_and_close(self):
    if self.name_field.text == '':
      self.error_label.text = 'Name cannot be blank.'
      return
    if re.match(r'^[0-9]{12}$', self.account_field.text) is None:
      self.error_label.text = 'Account ID must be a 12-digit number.'
      return
    if self.access_key_field.text == '':
      self.error_label.text = 'Access key cannot be blank.'
      return
    if self.secret_key_field.text == '':
      self.error_label.text = 'Secret key cannot be blank.'
      return
    try:
      Common.Session.service_provider.whoami(keys={'access': self.access_key_field.text, 'secret': self.secret_key_field.text})
    except exceptions.ClientError as e:
      self.error_label.text = 'Key verification failed'
      return

    self.accepts_inputs = False
    # TODO: Test credentials.
    Common.Configuration.add_or_edit_context(self.name_field.text, self.account_field.text, self.access_key_field.text, self.secret_key_field.text)
    self.close()

  def close(self):
    if self.caller is not None:
      self.caller.reload_contexts()
    self.parent.remove_block(self)

class ContextList(ListControl):
  def __init__(self, parent, alignment, dimensions, *args, **kwargs):
    super().__init__(
      parent,
      alignment,
      dimensions,
      color=Common.color('context_list_generic', 'generic'),
      selection_color=Common.color('context_list_selection', 'selection'),
      title_color=Common.color('context_list_heading', 'column_title'),
      *args,
      **kwargs,
    )
    self.hotkey_display = HotkeyDisplay(self.parent, TopRightAnchor(1, 0), Dimension('33%|50', 8), self, highlight_color=Common.color('hotkey_display_title'), generic_color=Common.color('hotkey_display_value'), tag='context')
    self.add_hotkey('a', self.add_new_context, 'Add new context')
    self.add_hotkey('d', self.set_default_context, 'Set as default')
    self.add_hotkey('KEY_ENTER', self.select_context, 'Select context')
    self.add_hotkey('\x04', self.delete_selected_context, 'Delete context')
    self.new_context_dialog = None
    self.add_column('account id', 12)
    self.add_column('default', 7)
    idx = 0

    self.reload_contexts()

  def reload_contexts(self):
    self.entries = []
    self.selected = 0
    idx = 0
    defa = 0
    for context, data in Common.Configuration['contexts'].items():
      if context == Common.Configuration['default_context']:
        defa = idx
        d = '✓'
      else:
        d = ' '
      self.add_entry(ListEntry(context, **{"account id": data["account_id"], "default": d}))

      idx += 1
    if self.selected >= len(self.entries) or self.selected < 0:
      self.selected = defa

  def add_new_context(self, _):
    AddContextDialog(self.parent, CenterAnchor(0, 0), Dimension('80%|40', '20'), caller=self, weight=-500)

  def set_default_context(self, _):
    if self.selection is not None:
      Common.Configuration['default_context'] = self.selection.name
      Common.Configuration.write_config()
      self.reload_contexts()

  def select_context(self, _):
    if self.selection is not None:
      Common.Session.context = self.selection.name

  def delete_selected_context(self, _):
    if self.selection is not None:
      DeleteContextDialog(self.parent, CenterAnchor(0, 0), Dimension('80%|40', 10), name=self.selection.name, caller=self, weight=-500)
