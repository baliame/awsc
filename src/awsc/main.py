from .common import Common, DefaultAnchor, DefaultDimension, DefaultBorder, BaseChart
from .termui.alignment import TopLeftAnchor, Dimension
from .termui.control import Border
from .context import ContextList
from .region import RegionList
from .ssh import SSHList
from .info import InfoDisplay
from .aws import AWS
from .commander import Commander, Filterer
from .resources import *
from .meta import CommanderOptionsLister
import os
import sys
import datetime

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
  return SSHList.opener()

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
  # stderr hack
  old_stderr = None
  try:
    if os.fstat(0) == os.fstat(1):
      tg = open('error.log', 'w', buffering=1)

      old_stderr = sys.stderr
      sys.stderr = tg

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
      'lc': LCResourceLister.opener,
      'launchconfiguration': LCResourceLister.opener,
      'r53': R53ResourceLister.opener,
      'route53': R53ResourceLister.opener,
      'cfn': CFNResourceLister.opener,
      'cloudformation': CFNResourceLister.opener,
      'rds': RDSResourceLister.opener,
      'lb': LBResourceLister.opener,
      'elbv2': LBResourceLister.opener,
      'loadbalancing': LBResourceLister.opener,
      'ami': AMIResourceLister.opener,
      'image': AMIResourceLister.opener,
      'ebs': EBSResourceLister.opener,
      'ec2': EC2ResourceLister.opener,
      'instance': EC2ResourceLister.opener,
      'asg': ASGResourceLister.opener,
      'autoscaling': ASGResourceLister.opener,
      'rt': RouteTableResourceLister.opener,
      'route': RouteResourceLister.opener,
      'routetable': RouteTableResourceLister.opener,
      'sg': SGResourceLister.opener,
      'securitygroup': SGResourceLister.opener,
      'subnet': SubnetResourceLister.opener,
      'tg': TargetGroupResourceLister.opener,
      'targetgroup': TargetGroupResourceLister.opener,
      'vpc': VPCResourceLister.opener,
      'dsg': DBSubnetGroupResourceLister.opener,
      'dbsubnetgroup': DBSubnetGroupResourceLister.opener,
      's3': S3ResourceLister.opener,
      'it': InstanceClassResourceLister.opener,
      'instancetype': InstanceClassResourceLister.opener,
      'instanceclass': InstanceClassResourceLister.opener,
      'key': KeyPairResourceLister.opener,
      'keypair': KeyPairResourceLister.opener,
      '?': CommanderOptionsLister.opener,
      'help': CommanderOptionsLister.opener,
    }

    Common.main()
  finally:
    if old_stderr is not None:
      sys.stderr.close()
      sys.stderr = old_stderr
