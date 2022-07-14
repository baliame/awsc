from .base_control import ResourceLister, Describer, MultiLister, NoResults, GenericDescriber, DialogFieldResourceListSelector, DeleteResourceDialog, SingleRelationLister
from .common import Common, SessionAwareDialog, BaseChart
from .termui.dialog import DialogControl, DialogFieldText, DialogFieldLabel, DialogFieldButton, DialogFieldCheckbox
from .termui.alignment import CenterAnchor, Dimension
from .termui.control import Border
from .termui.list_control import ListEntry
from .termui.ui import ControlCodes
from .ssh import SSHList
import subprocess
from pathlib import Path
import json
import jq
import botocore
import time
import datetime
from .arn import ARN

class R53ResourceLister(ResourceLister):
  prefix = 'r53_list'
  title = 'Route53 Hosted Zones'
  command_palette = ['r53', 'route53']

  def __init__(self, *args, **kwargs):
    self.resource_key = 'route53'
    self.list_method = 'list_hosted_zones'
    self.item_path = '.HostedZones'
    self.column_paths = {
      'id': '.Id',
      'name': '.Name',
      'records': '.ResourceRecordSetCount',
    }
    self.imported_column_sizes = {
      'id': 30,
      'name': 30,
      'records': 5,
    }
    self.describe_command = R53Describer.opener
    self.open_command = R53RecordLister.opener
    self.open_selection_arg = 'r53_entry'
    self.primary_key = 'id'

    self.imported_column_order = ['id', 'name', 'records']
    self.sort_column = 'name'
    super().__init__(*args, **kwargs)

class R53RecordLister(ResourceLister):
  prefix = 'r53_record_list'
  title = 'Route53 Records'

  def title_info(self):
    return self.r53_entry['name']

  def __init__(self, *args, r53_entry, **kwargs):
    self.r53_entry = r53_entry
    self.resource_key = 'route53'
    self.list_method = 'list_resource_record_sets'
    self.list_kwargs={'HostedZoneId': self.r53_entry['id']}
    self.item_path = '.ResourceRecordSets'
    self.column_paths = {
      'entry': '.Type',
      'name': self.determine_name,
      'records': self.determine_records,
      'ttl': '.TTL',
    }
    self.hidden_columns = {
      'hosted_zone_id': self.determine_hosted_zone_id,
    }
    self.imported_column_sizes = {
      'entry': 5,
      'name': 30,
      'records': 60,
      'ttl': 5,
    }
    self.describe_command = R53RecordDescriber.opener

    self.imported_column_order = ['entry', 'name', 'records', 'ttl']
    self.sort_column = 'name'
    self.primary_key = None
    super().__init__(*args, **kwargs)
    self.add_hotkey('e', self.edit, 'Edit')

  def determine_hosted_zone_id(self, s):
    return self.r53_entry['id']

  def determine_name(self, s):
    return s['Name'].replace('\\052', '*')

  def edit(self, _):
    if self.selection is not None:
      raw = self.selection.controller_data
      if not self.is_alias(raw):
        content = '\n'.join(record['Value'] for record in raw['ResourceRecords'])
        newcontent = Common.Session.textedit(content).strip(' \n\t')
        if content == newcontent:
          Common.Session.set_message('Input unchanged.', Common.color('message_info'))
          return
        newcontent = newcontent.split('\n')
        try:
          Common.Session.service_provider(self.resource_key).change_resource_record_sets(
            HostedZoneId=self.selection['hosted_zone_id'],
            ChangeBatch={
              'Changes': [{
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                  'Name': self.selection['name'],
                  'Type': self.selection['entry'],
                  'ResourceRecords': [{'Value': line} for line in newcontent],
                  'TTL': int(self.selection['ttl']),
                },
              }]
            }
          )
        except botocore.errorfactory.InvalidInput as e:
          Common.Session.ui.log(str(e))
          Common.Session.set_message('AWS API returned error, logged.', Common.color('message_error'))
          return
          Common.Session.set_message('Entry modified, refreshing...', Common.color('message_success'))

        self.refresh_data()
      else:
        Common.Session.set_message('Cannot edit aliased records', Common.color('message_info'))

  def is_alias(self, s):
    return 'AliasTarget' in s and s['AliasTarget']['DNSName'] != ''

  def determine_records(self, s):
    if self.is_alias(s):
      return s['AliasTarget']['DNSName']
    return ','.join([record['Value'] for record in s['ResourceRecords']])

class R53Describer(Describer):
  prefix = 'r53_browser'
  title = 'Route53 Hosted Zone'

  def __init__(self, parent, alignment, dimensions, entry, *args, entry_key='id', **kwargs):
    self.resource_key = 'route53'
    self.describe_method = 'get_hosted_zone'
    self.describe_kwarg_name = 'Id'
    self.object_path='.'
    super().__init__(parent, alignment, dimensions, *args, entry=entry, entry_key=entry_key, **kwargs)

class R53RecordDescriber(Describer):
  prefix = 'r53_record_browser'
  title = 'Route53 Record'

  def populate_entry(self, *args, entry, **kwargs):
    super().populate_entry(*args, entry=entry, **kwargs)
    self.record_type = entry['entry']
    self.record_name = entry['name']

  def populate_describe_kwargs(self, *args, **kwargs):
    super().populate_describe_kwargs(*args, **kwargs)
    self.describe_kwargs['StartRecordType'] = self.record_type
    self.describe_kwargs['StartRecordName'] = self.record_name

  def __init__(self, parent, alignment, dimensions, entry, *args, entry_key='hosted_zone_id', **kwargs):
    self.resource_key = 'route53'
    self.describe_method = 'list_resource_record_sets'
    self.describe_kwarg_name = 'HostedZoneId'
    self.object_path='.ResourceRecordSets[0]'
    super().__init__(parent, alignment, dimensions, *args, entry=entry, entry_key=entry_key, **kwargs)

  def title_info(self):
    return '{0} {1}'.format(self.record_type, self.record_name)
