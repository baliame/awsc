from .config.config import Config
from .termui.alignment import TopLeftAnchor, Dimension, CenterAnchor
from .session import Session
from .termui.bar_graph import BarGraph
from .termui.color import Color, Palette8Bit
from .termui.control import Border, BorderStyle
from .termui.dialog import DialogControl

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

  @staticmethod
  def initialize():
    Common.Configuration = Config()
    Common.Session = Session(Common.Configuration, Common.color('info_display_title'), Common.color('info_display_value'))

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