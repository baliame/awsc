import yaml

class Scheme:
  def __init__(self, config):
    self.style_file = config.path / 'style.yaml'
    self.config = config
    if not self.style_file.exists():
      self.create_default_config()
    else:
      self.parse_config()

  def backup_and_reset(self):
    print('Restoring style scheme to defaults. Creating backup of pre-restore scheme.')
    backup = self.config.path / 'style.yaml.bak'
    self.style_file.rename(backup)
    self.create_default_config()

  def create_default_config(self):
    print('Creating first time style scheme...')
    self.style = {
      'colors': {
        'generic': {
          'foreground': 220,
          'background': 0,
        },
        'highlight': {
          'foreground': 70,
          'background': 0,
        },
        'highlight_selection': {
          'foreground': 0,
          'background': 70,
        },
        'info_display_title': {
          'foreground': 70,
          'background': 0,
        },
        'info_display_value': {
          'foreground': 220,
          'background': 0,
        },
        'hotkey_display_title': {
          'foreground': 70,
          'background': 0,
        },
        'hotkey_display_value': {
          'foreground': 220,
          'background': 0,
        },
        'modal_dialog_label_highlight': {
          'foreground': 70,
          'background': 0,
        },
        'modal_dialog_label': {
          'foreground': 220,
          'background': 0,
        },
        'generic_border': {
          'foreground': 220,
          'background': 0,
        },
        'modal_dialog_border': {
          'foreground': 220,
          'background': 0,
        },
        'border_title': {
          'foreground': 111,
          'background': 0,
        },
        'border_title_info': {
          'foreground': 70,
          'background': 0,
        },
        'modal_dialog_border_title': {
          'foreground': 111,
          'background': 0,
        },
        'modal_dialog_border_title_info': {
          'foreground': 70,
          'background': 0,
        },
        'column_title': {
          'foreground': 0,
          'background': 208,
        },
        'message_success': {
          'foreground': 70,
          'background': 0,
        },
        'message_info': {
          'foreground': 33,
          'background': 0,
        },
        'message_error': {
          'foreground': 124,
          'background': 0,
        },
        'error': {
          'foreground': 124,
          'background': 0,
        },
        'modal_dialog_error': {
          'foreground': 124,
          'background': 0,
        },
        'selection': {
          'foreground': 0,
          'background': 220,
        },
        'textfield_label': {
          'foreground': 220,
          'background': 0,
        },
        'textfield': {
          'foreground': 0,
          'background': 208,
        },
        'textfield_selection': {
          'foreground': 0,
          'background': 220,
        },
        'button': {
          'foreground': 220,
          'background': 0,
        },
        'button_selection': {
          'foreground': 0,
          'background': 220,
        },
        'context_list_generic': {
          'foreground': 220,
          'background': 0,
        },
        'context_list_selection': {
          'foreground': 0,
          'background': 220,
        },
        'context_list_border': {
          'foreground': 220,
          'background': 0,
        },
        'context_list_border_title': {
          'foreground': 111,
          'background': 0,
        },
        'context_list_heading': {
          'foreground': 0,
          'background': 208,
        },
        'search_bar_border': {
          'foreground': 220,
          'background': 0,
        },
        'search_bar_color': {
          'foreground': 220,
          'background': 0,
        },
        'search_bar_symbol_color': {
          'foreground': 70,
          'background': 0,
        },
        'search_bar_autocomplete_color': {
          'foreground': 239,
          'background': 0,
        },
        'search_bar_inactive_color': {
          'foreground': 239,
          'background': 0,
        },
        'command_bar_border': {
          'foreground': 220,
          'background': 0,
        },
        'command_bar_color': {
          'foreground': 220,
          'background': 0,
        },
        'command_bar_symbol_color': {
          'foreground': 70,
          'background': 0,
        },
        'command_bar_autocomplete_color': {
          'foreground': 239,
          'background': 0,
        },
        'command_bar_ok_color': {
          'foreground': 33,
          'background': 0,
        },
        'command_bar_error_color': {
          'foreground': 124,
          'background': 0,
        },
        'modal_dialog_textfield': {
          'foreground': 0,
          'background': 208,
        },
        'modal_dialog_textfield_selected': {
          'foreground': 0,
          'background': 220,
        },
        'modal_dialog_textfield_label': {
          'foreground': 220,
          'background': 0,
        },
      },
      'borders': {
        'default': {
          'horizontal': '─',
          'vertical': '│',
          'TL': '┌',
          'TR': '┐',
          'BL': '└',
          'BR': '┘',
        },
        'search_bar': {
          'horizontal': '─',
          'vertical': '│',
          'TL': '┌',
          'TR': '┐',
          'BL': '└',
          'BR': '┘',
        },
        'modal': {
          'horizontal': '─',
          'vertical': '│',
          'TL': '┌',
          'TR': '┐',
          'BL': '└',
          'BR': '┘',
        },
        'resource_list': {
          'horizontal': '─',
          'vertical': '│',
          'TL': '┌',
          'TR': '┐',
          'BL': '└',
          'BR': '┘',
        },
      }
    }

    with self.style_file.open('w') as f:
      f.write(yaml.dump(self.style))

  def __getitem__(self, item):
    return self.style[item]

  def parse_config(self):
    with self.style_file.open('r') as f:
      self.style = yaml.safe_load(f.read())
