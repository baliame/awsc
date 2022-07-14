from .config.config import Config
from .termui.alignment import TopLeftAnchor, Dimension, CenterAnchor
from .session import Session
from .termui.bar_graph import BarGraph
from .termui.color import Color, Palette8Bit
from .termui.control import Border, BorderStyle
from .termui.dialog import DialogControl
from botocore import exceptions
import configparser
from pathlib import Path
import sys

DefaultAnchor = TopLeftAnchor(0, 11)
DefaultDimension = Dimension('100%', '100%-14')

class BaseChart(BarGraph):
  prefix = 'CHANGEME'
  title = 'CHANGEME'

  @classmethod
  def opener(cls, *args, **kwargs):
    ret = cls(
      Common.Session.ui.top_block,
      DefaultAnchor,
      DefaultDimension,
      *args,
      weight=0,
      color=Common.color('generic'),
      **kwargs
    )
    ret.border=DefaultBorder(cls.prefix, cls.title, ret.title_info())
    return [ret]

  def title_info(self):
    return None

class SessionAwareDialog(DialogControl):
  @classmethod
  def opener(cls, caller, *args, **kwargs):
    return cls(caller.parent, CenterAnchor(0, 0), Dimension('80%|40', '10'), caller=caller, *args, **kwargs)

  def __init__(self, *args, caller, **kwargs):
    caller.dialog_mode = True
    self.caller = caller
    Common.Session.extend_frame(self)
    kwargs['ok_action'] = self.accept_and_close
    kwargs['cancel_action'] = self.close
    super().__init__(*args, **kwargs)

  def input(self, inkey):
    if inkey.is_sequence and inkey.name == 'KEY_ESCAPE':
      self.close()
      return True
    return super().input(inkey)

  def accept_and_close(self):
    self.close()

  def close(self):
    self.caller.dialog_mode = False
    self.parent.remove_block(self)
    Common.Session.remove_from_frame(self)

class Common:
  Configuration = None
  Session = None
  initialized = False
  init_hooks = set()

  @classmethod
  def run_on_init(cls, hook):
    if cls.initialized:
      hook()
    else:
      cls.init_hooks.add(hook)

  @classmethod
  def initialize(cls):
    cls.Configuration = Config()
    cls.Session = Session(cls.Configuration, cls.color('info_display_title'), cls.color('info_display_value'))

  @classmethod
  def post_initialize(cls):
    for hook in cls.init_hooks:
      hook()
    cls.load_dot_aws()

  @classmethod
  def load_dot_aws(cls):
    aws_creds = Path.home() / '.aws' / 'credentials'
    print('Loading ~/.aws/credentials', file=sys.stderr)
    try:
      with aws_creds.open('r') as f:
        creds = f.read()
    except OSError as e:
      print('Failed to open ~/.aws/credentials: {0}'.format(str(e)), file=sys.stderr)
      return
    parser = configparser.ConfigParser(default_section="__default")
    parser.read_string(creds)
    for section in parser.sections():
      if 'aws_access_key_id' not in parser[section]:
        print('aws_access_key_id missing for credential {0}, skipping'.format(section), file=sys.stderr)
        continue
      if 'aws_secret_access_key' not in parser[section]:
        print('aws_secret_access_key missing for credential {0}, skipping'.format(section), file=sys.stderr)
        continue
      access = parser[section]['aws_access_key_id']
      secret = parser[section]['aws_secret_access_key']
      try:
        whoami = cls.Session.service_provider.whoami(keys={'access': access, 'secret': secret})
      except exceptions.ClientError as e:
        print('Failed to verify keys for credential {0}: {1}'.format(section, str(e)), file=sys.stderr)
        continue
      cls.Configuration.add_or_edit_context(section, whoami['Account'], access, secret)
      print('Added {0} context from aws credentials file'.format(section), file=sys.stderr)

  @staticmethod
  def color(name, fallback=None):
    if Common.Configuration is None:
      raise ValueError('Configuration is not initialized.')
    if name not in Common.Configuration.scheme['colors']:
      if fallback is None:
        raise KeyError('Undefined color "{0}"'.format(name))
      return Common.color(fallback)
    return Color(Palette8Bit(), Common.Configuration.scheme['colors'][name]['foreground'], background=Common.Configuration.scheme['colors'][name]['background'])

  @staticmethod
  def border(name, fallback=None):
    if Common.Configuration is None:
      raise ValueError('Configuration is not initialized.')
    if name not in Common.Configuration.scheme['borders']:
      if fallback is None:
        raise KeyError('Undefined border "{0}"'.format(name))
      return Common.border(fallback)
    border = Common.Configuration.scheme['borders'][name]
    return BorderStyle([border['horizontal'], border['vertical'], border['TL'], border['TR'], border['BL'], border['BR']])

  @staticmethod
  def main():
    Common.Session.ui.main()

def DefaultBorder(prefix, title, title_info=None):
  return Border(
    Common.border('resource_list', 'default'),
    Common.color('{0}_border'.format(prefix), 'generic_border'),
    title,
    Common.color('{0}_border_title'.format(prefix), 'border_title'),
    title_info,
    Common.color('{0}_border_title_info'.format(prefix), 'border_title_info'),
  )