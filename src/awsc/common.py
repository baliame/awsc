from .config.config import Config
from .termui.alignment import TopLeftAnchor, Dimension
from .session import Session
from .termui.color import Color, Palette8Bit
from .termui.control import Border, BorderStyle

DefaultAnchor = TopLeftAnchor(0, 11)
DefaultDimension = Dimension('100%', '100%-14')

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