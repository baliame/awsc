from .common import Common, DefaultAnchor, DefaultDimension, DefaultBorder
from .termui.alignment import TopLeftAnchor, Dimension
from .termui.control import Border
from .context import ContextList
from .region import RegionList
from .ssh import SSHList
from .info import InfoDisplay
from .aws import AWS
from .commander import Commander, Filterer
from .resources import *

def awscheck():
  return bool(Common.Session.context) and bool(Common.Session.region)

def open_context_lister():
  ctxl = ContextList(
    Common.Session.ui.top_block,
    DefaultAnchor,
    DefaultDimension,
    border=DefaultBorder('context_list', 'Contexts'),
    weight=0,
  )
  return [ctxl, ctxl.hotkey_display]

def open_region_lister():
  regl = RegionList(
    Common.Session.ui.top_block,
    DefaultAnchor,
    DefaultDimension,
    border=DefaultBorder('region_list', 'Regions'),
    weight = 0,
  )
  return [regl, regl.hotkey_display]

def open_ssh_lister():
  sshl = SSHList(
    Common.Session.ui.top_block,
    DefaultAnchor,
    DefaultDimension,
    border=DefaultBorder('ssh_key_list', 'SSH Keys'),
    weight = 0,
  )
  return [sshl, sshl.hotkey_display]

def open_filterer():
  if Common.Session.filterer is None:
    return Filterer(
      Common.Session.ui.top_block,
      TopLeftAnchor(0, 8),
      Dimension('100%', '3'),
      Common.Session,
      color=Common.color('search_bar_color'),
      symbol_color=Common.color('search_bar_symbol_color'),
      autocomplete_color=Common.color('search_bar_autocomplete_color'),
      inactive_color=Common.color('search_bar_inactive_color'),
      weight=-200,
      border=Border(Common.border('search_bar'), Common.color('search_bar_border')),
    )
  else:
    Common.Session.filterer.resume()

def open_commander():
  return Commander(
    Common.Session.ui.top_block,
    TopLeftAnchor(0, 8),
    Dimension('100%', '3'),
    Common.Session,
    color=Common.color('command_bar_color'),
    symbol_color=Common.color('command_bar_symbol_color'),
    autocomplete_color=Common.color('command_bar_autocomplete_color'),
    ok_color=Common.color('command_bar_ok_color'),
    error_color=Common.color('command_bar_error_color'),
    weight=-200,
    border=Border(Common.border('search_bar'), Common.color('search_bar_border')),
  )

def main(*args, **kwargs):
  Common.initialize()
  Common.Session.service_provider = AWS()
  Common.Session.replace_frame(open_context_lister())

  Common.Session.info_display.commander_hook = open_commander
  Common.Session.info_display.filterer_hook = open_filterer

  Common.Session.commander_options = {
    'ctx': open_context_lister,
    'context': open_context_lister,
    'region': open_region_lister,
    'ssh': open_ssh_lister,
    'cfn': CFNResourceLister.opener,
    'cloudformation': CFNResourceLister.opener,
    'rds': RDSResourceLister.opener,
    'ec2': EC2ResourceLister.opener,
    'instance': EC2ResourceLister.opener,
    'asg': ASGResourceLister.opener,
    'autoscaling': ASGResourceLister.opener,
    'sg': SGResourceLister.opener,
    'securitygroup': SGResourceLister.opener,
  }

  Common.main()
