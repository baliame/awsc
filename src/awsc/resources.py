from .resource_lister import ResourceLister, Describer, MultiLister, NoResults, GenericDescriber
from .common import Common, SessionAwareDialog
from .termui.dialog import DialogControl, DialogFieldText
from .termui.alignment import CenterAnchor, Dimension
from .termui.control import Border
from .termui.list_control import ListEntry
from .termui.ui import ControlCodes
import subprocess
from pathlib import Path
import json
import jq
import botocore
import time
import datetime
from .arn import ARN

def format_timedelta(delta):
  hours = int(delta.seconds / 3600)
  minutes = int(delta.seconds / 60) - hours * 60
  seconds = delta.seconds - hours * 3600 - minutes * 60
  if delta.days > 0:
    return '{0}d{1}h ago'.format(delta.days, hours)
  elif hours > 0:
    return '{0}h{1}m ago'.format(hours, minutes)
  elif minutes > 0:
    return '{0}m{1}s ago'.format(minutes, seconds)
  elif seconds > 0:
    return '{0}s ago'.format(seconds)
  else:
    return '<1s ago'

# AMI
class AMIResourceLister(ResourceLister):
  prefix = 'ami_list'
  title = 'Amazon Machine Images'

  def title_info(self):
    return self.title_info_data

  def __init__(self, *args, **kwargs):
    self.resource_key = 'ec2'
    self.list_method = 'describe_images'
    self.title_info_data = None
    self.list_kwargs = {'Owners': ['self']}
    if 'ec2' in kwargs:
      self.list_kwargs['ImageIds'] = [kwargs['ec2']['image']]
      self.title_info_data = 'Instance: {0}'.format(kwargs['ec2']['instance id'])
    self.item_path = '.Images'
    self.column_paths = {
      'id': '.ImageId',
      'name': '.Name',
      'arch': '.Architecture',
      'platform': '.PlatformDetails',
      'type': '.ImageType',
      'owner': '.ImageOwnerAlias',
      'state': '.State',
      'virt': '.VirtualizationType',
    }
    self.imported_column_sizes = {
      'id': 15,
      'name': 64,
      'arch': 8,
      'platform': 10,
      'type': 10,
      'owner': 15,
      'state': 10,
      'virt': 10,
    }
    self.describe_command = AMIDescriber.opener
    self.describe_selection_arg = 'ami_entry'
    self.imported_column_order = ['id', 'name', 'arch', 'platform', 'type', 'owner', 'state', 'virt']
    self.primary_key = 'id'
    self.sort_column = 'id'
    super().__init__(*args, **kwargs)

class AMIDescriber(Describer):
  prefix = 'ami_browser'
  title = 'Amazon Machine Image'

  def __init__(self, parent, alignment, dimensions, ami_entry, *args, **kwargs):
    self.ami_id = ami_entry['id']
    self.resource_key = 'ec2'
    self.describe_method = 'describe_images'
    self.describe_kwargs = {'ImageIds': [self.ami_id]}
    self.object_path='.Images[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.ami_id

# InstanceClasses
class InstanceClassResourceLister(ResourceLister):
  prefix = 'instance_class_list'
  title = 'Instance Classes'

  def __init__(self, *args, **kwargs):
    self.resource_key = 'ec2'
    self.list_method = 'describe_instance_types'
    self.item_path = '.InstanceTypes'
    self.list_kwargs = {'MaxResults': 20}
    self.column_paths = {
      'name': '.InstanceType',
      'cpus': '.VCpuInfo.DefaultVCpus',
      'memory': lambda x: '{0} MiB'.format(x['MemoryInfo']['SizeInMiB']),
      'ebs optimization': '.EbsInfo.EbsOptimizedSupport',
      'network': '.NetworkInfo.NetworkPerformance'
    }
    self.imported_column_sizes = {
      'name': 20,
      'cpus': 4,
      'memory': 10,
      'ebs optimization': 15,
      'network': 15,
    }
    self.next_marker = 'NextToken'
    self.next_marker_arg = 'NextToken'
    self.imported_column_order = ['name', 'cpus', 'memory', 'ebs optimization', 'network']
    self.sort_column = 'name'
    self.primary_key = 'name'
    self.describe_command = InstanceClassDescriber.opener
    self.describe_selection_arg = 'instance_class_entry'
    super().__init__(*args, **kwargs)

class InstanceClassDescriber(Describer):
  prefix = 'instance_class_browser'
  title = 'Instance Class'

  def __init__(self, parent, alignment, dimensions, instance_class_entry, *args, **kwargs):
    self.instance_class = instance_class_entry['name']
    self.resource_key = 'ec2'
    self.describe_method = 'describe_instance_types'
    self.describe_kwargs = {'InstanceTypes': [self.instance_class]}
    self.object_path='.InstanceTypes[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.instance_class

# EC2
class EC2ResourceLister(ResourceLister):
  prefix = 'ec2_list'
  title = 'EC2 Instances'

  def title_info(self):
    return self.title_info_data

  def __init__(self, *args, **kwargs):
    self.resource_key = 'ec2'
    self.list_method = 'describe_instances'
    self.title_info_data = None
    if 'asg' in kwargs:
      self.list_kwargs = {'Filters': [{'Name': 'tag:aws:autoscaling:groupName', 'Values': [kwargs['asg']['name']]}]}
      self.title_info_data = 'ASG: {0}'.format(kwargs['asg']['name'])
    self.item_path = '[.Reservations[].Instances[]]'
    self.column_paths = {
      'instance id': '.InstanceId',
      'name': self.tag_finder_generator('Name'),
      'type': '.InstanceType',
      'vpc': '.VpcId',
      'public ip': '.PublicIpAddress',
      'key name': '.KeyName',
      'state': '.State.Name',
    }
    self.imported_column_sizes = {
      'instance id': 11,
      'name': 30,
      'type': 10,
      'vpc': 15,
      'public ip': 15,
      'key name': 30,
      'state': 10,
    }
    self.hidden_columns = {
      'image': '.ImageId'
    }
    self.describe_command = EC2Describer.opener
    self.describe_selection_arg = 'instance_entry'
    self.imported_column_order = ['instance id', 'name', 'type', 'vpc', 'public ip', 'key name', 'state']
    self.sort_column = 'instance id'
    self.primary_key = 'instance id'
    super().__init__(*args, **kwargs)
    self.add_hotkey('s', self.ssh, 'Open SSH')

  def ssh(self, _):
    p = Path.home() / '.ssh' / Common.Session.ssh_key
    if not p.exists():
      Common.Session.set_message('Selected SSH key does not exist', Common.color('message_error'))
      return
    if self.selection is not None:
      if self.selection['public ip'] == '':
        Common.Session.set_message('No public IP associated with instance', Common.color('message_error'))
      else:
        EC2SSHDialog(self.parent, CenterAnchor(0, 0), Dimension('80%|40', '10'), instance_entry=self.selection, caller=self, weight=-500)

class EC2Describer(Describer):
  prefix = 'ec2_browser'
  title = 'EC2 Instance'

  def __init__(self, parent, alignment, dimensions, instance_entry, *args, **kwargs):
    self.instance_id = instance_entry['instance id']
    self.resource_key = 'ec2'
    self.describe_method = 'describe_instances'
    self.describe_kwargs = {'InstanceIds': [self.instance_id]}
    self.object_path='.Reservations[0].Instances[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.instance_id

class EC2SSHDialog(DialogControl):
  def __init__(self, parent, alignment, dimensions, instance_entry=None, caller=None, *args, **kwargs):
    kwargs['ok_action'] = self.accept_and_close
    kwargs['cancel_action'] = self.close
    kwargs['border'] = Border(
      Common.border('ec2_ssh', 'default'),
      Common.color('ec2_ssh_modal_dialog_border', 'modal_dialog_border'),
      'SSH to instance',
      Common.color('ec2_ssh_modal_dialog_border_title', 'modal_dialog_border_title'),
      instance_entry['instance id'],
      Common.color('ec2_ssh_modal_dialog_border_title_info', 'modal_dialog_border_title_info'),
    )
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    self.instance_id = instance_entry['instance id']
    self.ip = instance_entry['public ip']
    def_text = Common.Configuration['default_ssh_usernames'][Common.Session.ssh_key] if Common.Session.ssh_key in Common.Configuration['default_ssh_usernames'] else ''
    self.username_textfield = DialogFieldText(
      'SSH username',
      text=def_text,
      color=Common.color('ec2_ssh_modal_dialog_textfield', 'modal_dialog_textfield'),
      selected_color=Common.color('ec2_ssh_modal_dialog_textfield_selected', 'modal_dialog_textfield_selected'),
      label_color=Common.color('ec2_ssh_modal_dialog_textfield_label', 'modal_dialog_textfield_label'),
      label_min = 16,
    )
    self.add_field(self.username_textfield)
    self.highlighted = 1 if def_text != '' else 0
    self.caller = caller

  def input(self, inkey):
    if inkey.is_sequence and inkey.name == 'KEY_ESCAPE':
      self.close()
      return True
    return super().input(inkey)

  def accept_and_close(self):
    ph = Path.home() / '.ssh' / Common.Session.ssh_key
    ssh_cmd = '{0}@{1}'.format(self.username_textfield.text, self.ip)
    ex = Common.Session.ui.unraw(subprocess.run, ['bash', '-c', 'ssh -o StrictHostKeyChecking=no -i {0} {1}'.format(str(ph.resolve()), ssh_cmd)])
    Common.Session.set_message('ssh exited with code {0}'.format(ex.returncode), Common.color('message_info'))
    self.close()

  def close(self):
    self.parent.remove_block(self)

# ASG

class ASGResourceLister(ResourceLister):
  prefix = 'asg_list'
  title = 'Autoscaling Groups'

  def title_info(self):
    return self.title_info_data

  def matches(self, list_entry, *args):
    if self.lc is not None:
      if list_entry['launch config'] != self.lc['name']:
        return False
    return super().matches(list_entry, *args)

  def __init__(self, *args, **kwargs):
    self.resource_key = 'autoscaling'
    self.list_method = 'describe_auto_scaling_groups'
    self.title_info_data = None
    self.lc = None
    if 'lc' in kwargs:
      lc = kwargs['lc']
      self.title_info_data = 'LaunchConfiguration: {0}'.format(lc['name'])
      self.lc = lc

    self.item_path = '.AutoScalingGroups'
    self.column_paths = {
      'name': '.AutoScalingGroupName',
      'launch config/template': self.determine_launch_info,
      'current': self.determine_instance_count,
      'min': '.MinSize',
      'desired': '.DesiredCapacity',
      'max': '.MaxSize',
    }
    self.hidden_columns = {
      'launch config': '.LaunchConfigurationName',
      'arn': '.AutoScalingGroupARN',
    }
    self.imported_column_sizes = {
      'name': 30,
      'launch config/template': 30,
      'current': 10,
      'min': 10,
      'desired': 10,
      'max': 10,
    }
    self.describe_command = ASGDescriber.opener
    self.describe_selection_arg = 'asg_entry'
    self.open_command = EC2ResourceLister.opener
    self.open_selection_arg = 'asg'
    self.imported_column_order = ['name', 'launch config/template', 'current', 'min', 'desired', 'max']
    self.sort_column = 'name'
    self.primary_key = 'name'
    super().__init__(*args, **kwargs)

  def determine_launch_info(self, asg):
    if 'LaunchConfigurationName' in asg and bool(asg['LaunchConfigurationName']):
      return asg['LaunchConfigurationName']
    elif 'LaunchTemplate' in asg:
      return asg['LaunchTemplate']['LaunchTemplateName']
    else:
      return ''

  def determine_instance_count(self, asg):
    return '{0}/{1}'.format(len([h for h in asg['Instances'] if h['HealthStatus'] == 'Healthy']), len(asg['Instances']))

class ASGDescriber(Describer):
  prefix = 'asg_browser'
  title = 'Autoscaling Group'

  def __init__(self, parent, alignment, dimensions, asg_entry, *args, **kwargs):
    self.asg_name = asg_entry['name']
    self.resource_key = 'autoscaling'
    self.describe_method = 'describe_auto_scaling_groups'
    self.describe_kwargs = {'AutoScalingGroupNames': [self.asg_name]}
    self.object_path='.AutoScalingGroups[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.asg_name

# SecGroup

class SGResourceLister(ResourceLister):
  prefix = 'sg_list'
  title = 'Security Groups'

  def __init__(self, *args, **kwargs):
    self.resource_key = 'ec2'
    self.list_method = 'describe_security_groups'
    self.item_path = '.SecurityGroups'
    self.column_paths = {
      'group id': '.GroupId',
      'name': '.GroupName',
      'vpc': '.VpcId',
      'ingress rules': self.determine_ingress_rules,
      'egress rules': self.determine_egress_rules,
    }
    self.imported_column_sizes = {
      'group id': 30,
      'name': 30,
      'vpc': 15,
      'ingress rules': 20,
      'egress rules': 20,
    }
    self.describe_command = SGDescriber.opener
    self.describe_selection_arg = 'sg_entry'
    self.open_command = SGRelated.opener
    self.open_selection_arg = 'compare_value'

    self.imported_column_order = ['group id', 'name', 'vpc', 'ingress rules', 'egress rules']
    self.sort_column = 'name'
    self.primary_key = 'group id'
    super().__init__(*args, **kwargs)
    self.add_hotkey('i', self.ingress, 'View ingress rules')
    self.add_hotkey('e', self.egress, 'View egress rules')

  def determine_ingress_rules(self, sg):
    return len(sg['IpPermissions'])

  def determine_egress_rules(self, sg):
    return len(sg['IpPermissionsEgress'])

  def ingress(self, *args):
    if self.selection is not None:
      Common.Session.push_frame(SGRuleLister.opener(sg_entry=self.selection))

  def egress(self, *args):
    if self.selection is not None:
      Common.Session.push_frame(SGRuleLister.opener(sg_entry=self.selection, egress=True))

class SGRuleLister(ResourceLister):
  prefix = 'sg_rule_list'
  title = 'SG Rules'
  well_known = {
    20: 'ftp',
    22: 'ssh',
    23: 'telnet',
    25: 'smtp',
    80: 'http',
    110: 'pop3',
    220: 'imap',
    443: 'https',
    989: 'ftps',
    1437: 'dashboard-agent',
    1443: 'mssql',
    3306: 'mysql',
    3389: 'rdp',
    5432: 'pgsql',
    6379: 'redis',
    8983: 'solr',
    9200: 'es',
  }

  def title_info(self):
    return '{0}: {1}'.format('Egress' if self.egress else 'Ingress', self.sg_entry['group id'])

  def __init__(self, parent, alignment, dimensions, sg_entry=None, egress=False, *args, **kwargs):
    self.resource_key = 'ec2'
    self.list_method = 'describe_security_groups'
    if sg_entry is None:
      raise ValueError('sg_entry is required')
    self.sg_entry = sg_entry
    self.egress = egress
    self.list_kwargs = {'GroupIds': [self.sg_entry['group id']]}
    self.item_path = '.SecurityGroups[0].IpPermissions{0}'.format('Egress' if egress else '')
    self.column_paths = {
      'protocol': self.determine_protocol,
      'name': self.determine_name,
      'ip addresses': self.determine_ips,
      'security groups': self.determine_sgs,
      'port range': self.determine_port_range,
    }
    self.imported_column_sizes = {
      'name': 10,
      'protocol': 5,
      'ip addresses': 40,
      'security groups': 50,
      'port range': 20,
    }
    self.imported_column_order = ['name', 'protocol', 'ip addresses', 'security groups', 'port range']
    self.sort_column = 'port range'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def determine_name(self, rule):
    if rule['FromPort'] != rule['ToPort']:
      return ''
    if rule['FromPort'] not in SGRuleLister.well_known:
      return ''
    return SGRuleLister.well_known[rule['FromPort']]

  def determine_protocol(self, rule):
    if rule['IpProtocol'] == '-1' or rule['IpProtocol'] == -1:
      return 'all'
    return rule['IpProtocol']

  def determine_ips(self, rule):
    if 'IpRanges' not in rule:
      return ''
    return ','.join(cidrs['CidrIp'] for cidrs in rule['IpRanges'])

  def determine_sgs(self, rule):
    if 'UserIdGroupPairs' not in rule:
      return ''
    return ','.join(pair['GroupId'] for pair in rule['UserIdGroupPairs'])

  def determine_port_range(self, rule):
    if rule['FromPort'] != rule['ToPort']:
      return '{0}-{1}'.format(rule['FromPort'], rule['ToPort'])
    return str(rule['FromPort'])

class SGDescriber(Describer):
  prefix = 'sg_browser'
  title = 'Security Group'

  def __init__(self, parent, alignment, dimensions, sg_entry, *args, **kwargs):
    self.sg_id = sg_entry['group id']
    self.resource_key = 'ec2'
    self.describe_method = 'describe_security_groups'
    self.describe_kwargs = {'GroupIds': [self.sg_id]}
    self.object_path='.SecurityGroups[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.sg_id

class SGRelated(MultiLister):
  prefix = 'sg_related'
  title = 'Resources using Security Group'

  def title_info(self):
    return self.compare_value

  def __init__(self, *args, **kwargs):
    kwargs['compare_key'] = 'group id'
    self.resource_descriptors = [
      {
        'resource_key': 'ec2',
        'list_method': 'describe_instances',
        'list_kwargs': {},
        'item_path': '[.Reservations[].Instances[]]',
        'column_paths': {
          'type': lambda x: 'EC2 Instance',
          'id': '.InstanceId',
          'name': self.determine_ec2_name,
        },
        'hidden_columns': {},
        'compare_as_list': True,
        'compare_path': '[.SecurityGroups[].GroupId]',
      },
      {
        'resource_key': 'rds',
        'list_method': 'describe_db_instances',
        'list_kwargs': {},
        'item_path': '.DBInstances',
        'column_paths': {
          'type': lambda x: 'RDS Instance',
          'id': '.DBInstanceIdentifier',
          'name': self.determine_rds_name,
        },
        'hidden_columns': {},
        'compare_as_list': True,
        'compare_path': '[.VpcSecurityGroups[].VpcSecurityGroupId]',
      },
    ]
    super().__init__(*args, **kwargs)

# RDS

class RDSResourceLister(ResourceLister):
  prefix = 'rds_list'
  title = 'RDS Instances'

  def title_info(self):
    return self.title_info_data

  def __init__(self, *args, **kwargs):
    self.resource_key = 'rds'
    self.list_method = 'describe_db_instances'
    self.title_info_data = None
    self.item_path = '.DBInstances'
    self.column_paths = {
      'instance id': '.DBInstanceIdentifier',
      'host': '.Endpoint.Address',
      'engine': '.Engine',
      'type': '.DBInstanceClass',
      'vpc': '.DBSubnetGroup.VpcId',
    }
    self.hidden_columns = {
      'public_access': '.PubliclyAccessible',
      'db_name': '.DBName',
      'name': self.tag_finder_generator('Name', taglist_key='TagList'),
    }
    self.imported_column_sizes = {
      'instance id': 11,
      'host': 45,
      'engine': 10,
      'type': 10,
      'vpc': 15,
    }
    self.describe_command = RDSDescriber.opener
    self.describe_selection_arg = 'instance_entry'
    self.imported_column_order = ['instance id', 'host', 'engine', 'type', 'vpc']
    self.sort_column = 'instance id'
    self.primary_key = 'instance id'
    super().__init__(*args, **kwargs)
    self.add_hotkey('s', self.db_client, 'Open command line')

  def db_client(self, _):
    if self.selection is not None:
      if self.selection['public_access'] != 'True':
        Common.Session.set_message('No public IP associated with instance', Common.color('message_error'))
      else:
        RDSClientDialog(self.parent, CenterAnchor(0, 0), Dimension('80%|40', '10'), instance_entry=self.selection, caller=self, weight=-500)

class RDSDescriber(Describer):
  prefix = 'rds_browser'
  title = 'RDS Instance'

  def __init__(self, parent, alignment, dimensions, instance_entry, *args, **kwargs):
    self.instance_id = instance_entry['instance id']
    self.resource_key = 'rds'
    self.describe_method = 'describe_db_instances'
    self.describe_kwargs = {'DBInstanceIdentifier': self.instance_id}
    self.object_path='.DBInstances[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.instance_id

class RDSClientDialog(DialogControl):
  def __init__(self, parent, alignment, dimensions, instance_entry=None, caller=None, *args, **kwargs):
    kwargs['ok_action'] = self.accept_and_close
    kwargs['cancel_action'] = self.close
    kwargs['border'] = Border(
      Common.border('rds_client_modal', 'default'),
      Common.color('rds_client_modal_dialog_border', 'modal_dialog_border'),
      'SSH to instance',
      Common.color('rds_client_modal_dialog_border_title', 'modal_dialog_border_title'),
      instance_entry['instance id'],
      Common.color('rds_client_modal_dialog_border_title_info', 'modal_dialog_border_title_info'),
    )
    super().__init__(parent, alignment, dimensions, *args, **kwargs)
    self.instance_id = instance_entry['instance id']
    self.db_name = instance_entry['db_name']
    self.ip = instance_entry['host']
    self.engine = instance_entry['engine']
    self.username_textfield = DialogFieldText(
      'Username',
      text='',
      color=Common.color('rds_client_modal_dialog_textfield', 'modal_dialog_textfield'),
      selected_color=Common.color('rds_client_modal_dialog_textfield_selected', 'modal_dialog_textfield_selected'),
      label_color=Common.color('rds_client_modal_dialog_textfield_label', 'modal_dialog_textfield_label'),
      label_min = 16,
    )
    self.password_textfield = DialogFieldText(
      'Password',
      text='',
      color=Common.color('rds_client_modal_dialog_textfield', 'modal_dialog_textfield'),
      selected_color=Common.color('rds_client_modal_dialog_textfield_selected', 'modal_dialog_textfield_selected'),
      label_color=Common.color('rds_client_modal_dialog_textfield_label', 'modal_dialog_textfield_label'),
      label_min = 16,
      password = True,
    )
    self.database_textfield = DialogFieldText(
      'Database',
      text=self.db_name,
      color=Common.color('rds_client_modal_dialog_textfield', 'modal_dialog_textfield'),
      selected_color=Common.color('rds_client_modal_dialog_textfield_selected', 'modal_dialog_textfield_selected'),
      label_color=Common.color('rds_client_modal_dialog_textfield_label', 'modal_dialog_textfield_label'),
      label_min = 16,
    )
    self.add_field(self.username_textfield)
    self.add_field(self.password_textfield)
    self.add_field(self.database_textfield)
    self.highlighted = 1 if def_text != '' else 0
    self.caller = caller

  def input(self, inkey):
    if inkey.is_sequence and inkey.name == 'KEY_ESCAPE':
      self.close()
      return True
    return super().input(inkey)

  def accept_and_close(self):
    if self.engine in ['aurora', 'aurora-mysql', 'mariadb', 'mysql']:
      dollar_zero = 'mysql'
      cmd = 'mysql -h {0} -D {1} -u {2} --password={3}'.format(self.ip, self.database_textfield.text, self.username_textfield.text, self.password_textfield.text)
    elif self.engine in ['aurora-postgresql', 'postgres']:
      dollar_zero = 'psql'
      cmd = 'psql postgres://{2}:{3}@{0}/{1}'.format(self.ip, self.database_textfield.text, self.username_textfield.text, self.password_textfield.text)
    else:
      Common.Session.set_message('Unsupported engine: {0}'.format(self.engine), Common.color('message_info'))
      self.close()
      return
    ex = Common.Session.ui.unraw(subprocess.run, ['bash', '-c', cmd])
    Common.Session.set_message('{1} exited with code {0}'.format(ex.returncode, dollar_zero), Common.color('message_info'))
    self.close()

  def close(self):
    self.parent.remove_block(self)

# CFN

class CFNResourceLister(ResourceLister):
  prefix = 'cfn_list'
  title = 'CloudFormation Stacks'

  def __init__(self, *args, **kwargs):
    self.resource_key = 'cloudformation'
    self.list_method = 'describe_stacks'
    self.item_path = '.Stacks'
    self.column_paths = {
      'name': '.StackName',
      'status': '.StackStatus',
      'drift': '.DriftInformation.StackDriftStatus',
      'created': self.determine_created,
      'updated': self.determine_updated,
    }
    self.hidden_columns = {
      'arn': '.StackId',
    }
    self.imported_column_sizes = {
      'name': 30,
      'status': 15,
      'drift': 15,
      'created': 20,
      'updated': 20,
    }
    self.describe_command = CFNDescriber.opener
    self.describe_selection_arg = 'cfn_entry'
    self.open_command = CFNRelated.opener
    self.open_selection_arg = 'compare_value'

    self.imported_column_order = ['name', 'status', 'drift', 'created', 'updated']
    self.sort_column = 'name'
    self.primary_key = 'name'
    super().__init__(*args, **kwargs)

  def determine_created(self, cfn):
    return format_timedelta(datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(cfn['CreationTime']))

  def determine_updated(self, cfn):
    return format_timedelta(datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(cfn['LastUpdatedTime']))

class CFNDescriber(Describer):
  prefix = 'cfn_browser'
  title = 'CloudFormation Stack'

  def __init__(self, parent, alignment, dimensions, sg_entry, *args, **kwargs):
    self.stack_name = sg_entry['name']
    self.resource_key = 'cloudformation'
    self.describe_method = 'describe_stacks'
    self.describe_kwargs = {'StackName': self.stack_name}
    self.object_path='.Stacks[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.stack_name

class CFNRelated(MultiLister):
  prefix = 'cfn_related'
  title = 'Resources in CloudFormation Stack'

  def title_info(self):
    return self.compare_value

  def __init__(self, *args, **kwargs):
    kwargs['compare_key'] = 'arn'
    self.resource_descriptors = [
      {
        'resource_key': 'ec2',
        'list_method': 'describe_instances',
        'list_kwargs': {},
        'item_path': '[.Reservations[].Instances[]]',
        'column_paths': {
          'type': lambda x: 'EC2 Instance',
          'id': '.InstanceId',
          'name': self.tag_finder_generator('Name'),
        },
        'hidden_columns': {},
        'compare_as_list': False,
        'compare_path': '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
      },
      {
        'resource_key': 'autoscaling',
        'list_method': 'describe_auto_scaling_groups',
        'list_kwargs': {},
        'item_path': '.AutoScalingGroups',
        'column_paths': {
          'type': lambda x: 'Autoscaling Group',
          'id': self.empty,
          'name': '.AutoScalingGroupName',
        },
        'hidden_columns': {},
        'compare_as_list': False,
        'compare_path': '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
      },
      {
        'resource_key': 'rds',
        'list_method': 'describe_db_instances',
        'list_kwargs': {},
        'item_path': '.DBInstances',
        'column_paths': {
          'type': lambda x: 'RDS Instance',
          'id': '.DBInstanceIdentifier',
          'name': '.Endpoint.Address',
        },
        'hidden_columns': {},
        'compare_as_list': False,
        'compare_path': '.TagList[] | select(.Key=="aws:cloudformation:stack-id").Value',
      },
      {
        'resource_key': 'elbv2',
        'list_method': 'describe_load_balancers',
        'list_kwargs': {},
        'item_path': '.LoadBalancers',
        'column_paths': {
          'type': lambda x: 'Load Balancer',
          'id': self.empty,
          'name': '.LoadBalancerName',
        },
        'hidden_columns': {
          'arn': '.LoadBalancerArn',
        },
        'compare_as_list': False,
        'compare_path': self.comparer_generator('AWS::ElasticLoadBalancingV2::LoadBalancer', '.LoadBalancerArn'),
      },
      {
        'resource_key': 'elbv2',
        'list_method': 'describe_target_groups',
        'list_kwargs': {},
        'item_path': '.TargetGroups',
        'column_paths': {
          'type': lambda x: 'Target Group',
          'id': self.resource_id_from_arn_generator('.TargetGroupArn'),
          'name': '.TargetGroupName',
        },
        'hidden_columns': {
          'arn': '.TargetGroupArn',
        },
        'compare_as_list': False,
        'compare_path': self.comparer_generator('AWS::ElasticLoadBalancingV2::TargetGroup', '.TargetGroupArn'),
      },
      {
        'resource_key': 'elbv2',
        'list_method': 'describe_listeners',
        'list_kwargs': self.kwargs_from_physids_generator('ListenerArns', 'AWS::ElasticLoadBalancingV2::Listener'),
        'item_path': '.Listeners',
        'column_paths': {
          'type': lambda x: 'Listener',
          'id': self.full_resource_id_from_arn_generator('.ListenerArn'),
          'name': self.empty,
        },
        'hidden_columns': {
          'arn': '.ListenerArn',
        },
        'compare_as_list': False,
        'compare_path': self.comparer_generator('AWS::ElasticLoadBalancingV2::Listener', '.ListenerArn'),
      },
      {
        'resource_key': 'ec2',
        'list_method': 'describe_vpcs',
        'list_kwargs': {},
        'item_path': '.Vpcs',
        'column_paths': {
          'type': lambda x: 'VPC',
          'id': '.VpcId',
          'name': self.tag_finder_generator('Name'),
        },
        'hidden_columns': {},
        'compare_as_list': False,
        'compare_path': '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
      },
      {
        'resource_key': 'ec2',
        'list_method': 'describe_subnets',
        'list_kwargs': {},
        'item_path': '.Subnets',
        'column_paths': {
          'type': lambda x: 'VPC Subnet',
          'id': '.SubnetId',
          'name': self.tag_finder_generator('Name'),
        },
        'hidden_columns': {},
        'compare_as_list': False,
        'compare_path': '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
      },
      {
        'resource_key': 'route53',
        'list_method': 'list_hosted_zones',
        'list_kwargs': {},
        'item_path': '.HostedZones',
        'column_paths': {
          'type': lambda x: 'Route53 Zone',
          'id': '.Id',
          'name': '.Name',
        },
        'hidden_columns': {},
        'compare_as_list': False,
        'compare_path': self.comparer_generator('AWS::Route53::HostedZone', '.Id'),
      },
      {
        'resource_key': 'ec2',
        'list_method': 'describe_vpcs',
        'list_kwargs': {},
        'item_path': '.Vpcs',
        'column_paths': {
          'type': lambda x: 'VPC',
          'id': '.VpcId',
          'name': self.tag_finder_generator('Name'),
        },
        'hidden_columns': {},
        'compare_as_list': False,
        'compare_path': '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
      },
      {
        'resource_key': 'ec2',
        'list_method': 'describe_subnets',
        'list_kwargs': {},
        'item_path': '.Subnets',
        'column_paths': {
          'type': lambda x: 'Subnet',
          'id': '.SubnetId',
          'name': self.tag_finder_generator('Name'),
        },
        'hidden_columns': {},
        'compare_as_list': False,
        'compare_path': '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
      },
      {
        'resource_key': 'ec2',
        'list_method': 'describe_route_tables',
        'list_kwargs': {},
        'item_path': '.RouteTables',
        'column_paths': {
          'type': lambda x: 'Route Table',
          'id': '.RouteTableId',
          'name': self.tag_finder_generator('Name'),
        },
        'hidden_columns': {},
        'compare_as_list': False,
        'compare_path': '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
      }
    ]
    super().__init__(*args, **kwargs)

  def full_resource_id_from_arn_generator(self, arn_path):
    def fn(raw_item):
      arn = ARN(Common.Session.jq(arn_path).input(raw_item).first())
      return arn.resource_id
    return fn

  def resource_id_from_arn_generator(self, arn_path):
    def fn(raw_item):
      arn = ARN(Common.Session.jq(arn_path).input(raw_item).first())
      return arn.resource_id_first
    return fn

  def comparer_generator(self, cfn_type, physical_id_path):
    def fn(raw_item):
      phys_id = Common.Session.jq(physical_id_path).input(raw_item).first()
      if cfn_type in self.stack_res_list and phys_id in self.stack_res_list[cfn_type]:
        return self.compare_value
      return None
    return fn

  def kwargs_from_physids_generator(self, kwarg, cfn_type):
    def fn():
      if cfn_type in self.stack_res_list:
        return {kwarg: self.stack_res_list[cfn_type]}
      raise NoResults
    return fn

  def async_inner(self, *args, fn, clear=False, **kwargs):
    stop = False
    rl = None
    self.stack_res_list = {}
    while not stop:
      rargs = {'StackName': self.orig_compare_value['name']}
      if rl is not None and 'NextToken' in rl and rl['NextToken'] is not None:
        rargs['NextToken'] = rl['NextToken']
      rl = Common.Session.service_provider('cloudformation').list_stack_resources(**rargs)
      if 'NextToken' not in rl or rl['NextToken'] is None:
        stop = True
      for item in rl['StackResourceSummaries']:
        if item['ResourceType'] not in self.stack_res_list:
          self.stack_res_list[item['ResourceType']] = []
        self.stack_res_list[item['ResourceType']].append(item['PhysicalResourceId'])
    return super().async_inner(*args, fn=fn, clear=clear, **kwargs)

# R53

class R53ResourceLister(ResourceLister):
  prefix = 'r53_list'
  title = 'Route53 Hosted Zones'

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
    self.describe_selection_arg = 'r53_entry'
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
    self.describe_selection_arg = 'r53_entry'

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

  def __init__(self, parent, alignment, dimensions, r53_entry, *args, **kwargs):
    self.r53_entry = r53_entry
    self.resource_key = 'route53'
    self.describe_method = 'get_hosted_zone'
    self.describe_kwargs = {'Id': self.r53_entry['id']}
    self.object_path='.'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.r53_entry['name']

class R53RecordDescriber(Describer):
  prefix = 'r53_record_browser'
  title = 'Route53 Record'

  def __init__(self, parent, alignment, dimensions, r53_entry, *args, **kwargs):
    self.r53_entry = r53_entry
    self.resource_key = 'route53'
    self.describe_method = 'list_resource_record_sets'
    self.describe_kwargs = {'HostedZoneId': self.r53_entry['hosted_zone_id'], 'StartRecordType': self.r53_entry['entry'], 'StartRecordName': self.r53_entry['name']}
    self.object_path='.ResourceRecordSets[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return '{0} {1}'.format(self.r53_entry['entry'], self.r53_entry['name'])

# LC
class LCResourceLister(ResourceLister):
  prefix = 'lc_list'
  title = 'Launch Configurations'

  def __init__(self, *args, **kwargs):
    self.resource_key = 'autoscaling'
    self.list_method = 'describe_launch_configurations'
    self.item_path = '.LaunchConfigurations'
    self.column_paths = {
      'name': '.LaunchConfigurationName',
      'image id': '.ImageId',
      'instance type': '.InstanceType',
    }
    self.imported_column_sizes = {
      'name': 30,
      'image id': 20,
      'instance type': 20,
    }
    self.describe_command = LCDescriber.opener
    self.describe_selection_arg = 'lc_entry'
    self.open_command = ASGResourceLister.opener
    self.open_selection_arg = 'lc'

    self.imported_column_order = ['name', 'image id', 'instance type']
    self.sort_column = 'name'
    super().__init__(*args, **kwargs)

class LCDescriber(Describer):
  prefix = 'lc_browser'
  title = 'Launch Configuration'

  def __init__(self, parent, alignment, dimensions, lc_entry, *args, **kwargs):
    self.lc_name = lc_entry['name']
    self.resource_key = 'autoscaling'
    self.describe_method = 'describe_launch_configurations'
    self.describe_kwargs = {'LaunchConfigurationNames': [self.lc_name]}
    self.object_path='.LaunchConfigurations[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.lc_name

# LB
class LBResourceLister(ResourceLister):
  prefix = 'lb_list'
  title = 'Load Balancers'

  def __init__(self, *args, **kwargs):
    self.resource_key = 'elbv2'
    self.list_method = 'describe_load_balancers'
    self.item_path = '.LoadBalancers'
    self.column_paths = {
      'name': '.LoadBalancerName',
      'type': '.Type',
      'scheme': self.determine_scheme,
      'hostname': '.DNSName',
    }
    self.imported_column_sizes = {
      'name': 30,
      'type': 15,
      'scheme': 8,
      'hostname': 120,
    }
    self.hidden_columns = {
      'arn': '.LoadBalancerArn',
    }
    self.describe_command = LBDescriber.opener
    self.describe_selection_arg = 'lb_entry'
    self.open_command = ListenerResourceLister.opener
    self.open_selection_arg = 'lb'

    self.imported_column_order = ['name', 'type', 'scheme', 'hostname']
    self.sort_column = 'name'
    self.primary_key = 'name'
    super().__init__(*args, **kwargs)

  def determine_scheme(self, lb, *args):
    if lb['Scheme'] == 'internet-facing':
      return 'public'
    return 'private'

class LBDescriber(Describer):
  prefix = 'lb_browser'
  title = 'Load Balancer'

  def __init__(self, parent, alignment, dimensions, lb_entry, *args, **kwargs):
    self.lb_name = lb_entry['name']
    self.resource_key = 'elbv2'
    self.describe_method = 'describe_load_balancers'
    self.describe_kwargs = {'Names': [self.lb_name]}
    self.object_path='.LoadBalancers[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.lb_name

# Listener
class ListenerResourceLister(ResourceLister):
  prefix = 'listener_list'
  title = 'Listeners'

  def title_info(self):
    return self.lb['name']

  def __init__(self, *args, **kwargs):
    self.resource_key = 'elbv2'
    self.list_method = 'describe_listeners'
    self.item_path = '.Listeners'
    self.lb = kwargs['lb']
    self.list_kwargs = {'LoadBalancerArn': self.lb['arn']}
    self.column_paths = {
      'protocol': '.Protocol',
      'port': '.Port',
      'ssl policy': self.determine_ssl_policy,
    }
    self.imported_column_sizes = {
      'protocol': 10,
      'port': 10,
      'ssl policy': 30,
    }
    self.hidden_columns = {
      'arn': '.ListenerArn',
      'name': '.ListenerArn',
    }
    self.describe_command = ListenerDescriber.opener
    self.describe_selection_arg = 'listener_entry'
    self.open_command = ListenerActionResourceLister.opener
    self.open_selection_arg = 'listener'
    self.primary_key = 'arn'

    self.imported_column_order = ['protocol', 'port', 'ssl policy']
    self.sort_column = 'arn'
    super().__init__(*args, **kwargs)

  def determine_ssl_policy(self, l, *args):
    if l['Protocol'] == 'HTTPS':
      return l['SslPolicy']
    return ''

class ListenerDescriber(Describer):
  prefix = 'listener_browser'
  title = 'Listener'

  def __init__(self, parent, alignment, dimensions, listener_entry, *args, **kwargs):
    self.listener_arn = listener_entry['name']
    self.resource_key = 'elbv2'
    self.describe_method = 'describe_listeners'
    self.describe_kwargs = {'ListenerArns': [self.listener_arn]}
    self.object_path='.Listeners[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.listener_arn

# Action
class ListenerActionResourceLister(ResourceLister):
  prefix = 'listener_action_list'
  title = 'Listener Rules'

  def title_info(self):
    return self.listener['name']

  def __init__(self, *args, **kwargs):
    self.resource_key = 'elbv2'
    self.list_method = 'describe_rules'
    self.item_path = '.Rules'
    self.listener = kwargs['listener']
    self.list_kwargs = {'ListenerArn': self.listener['arn']}
    self.column_paths = {
      'prio': '.Priority',
      'condition': self.determine_condition,
      'action type': self.determine_action_type,
      'target': self.determine_target,
    }
    self.imported_column_sizes = {
      'prio': 10,
      'condition': 40,
      'action type': 20,
      'target': 120,
    }
    self.hidden_columns = {
      'name': '.RuleArn',
      'arn': '.RuleArn',
    }
    self.describe_command = ListenerActionDescriber.opener
    self.describe_selection_arg = 'listener_entry'
    self.open_command = TargetGroupResourceLister.opener
    self.open_selection_arg = 'rule_entry'

    self.imported_column_order = ['prio', 'condition', 'action type', 'target']
    self.sort_column = 'prio'
    super().__init__(*args, **kwargs)

  def open(self, *args):
    if self.selection is not None:
      if self.selection['action type'] == 'forward':
        return super().open(*args)
      else:
        return self.describe(*args)

  def determine_condition(self, la, *args):
    if len(la['Conditions']) > 1:
      return '<multiple>'
    elif len(la['Conditions']) == 1:
      cond = la['Conditions'][0]
      field = cond['Field']
      if field == 'host-header':
        if 'Values' in cond and len(cond['Values']):
          if isinstance(cond['Values'], str):
            return 'Host: {0}'.format(cond['Values'])
          else:
            src = cond['Values']
        else:
          src = cond['HostHeaderConfig']['Values']
        return 'Host: {0}'.format('|'.join(src))
      elif field == 'path':
        if 'Values' in cond and len(cond['Values']):
          if isinstance(cond['Values'], str):
            return 'Path: {0}'.format(cond['Values'])
          else:
            src = cond['Values']
        else:
          src = cond['PathPatternConfig']['Values']
        return 'Path: {0}'.format('|'.join(src))

      return field
    else:
      return '<always>'

  def determine_action_type(self, l, *args):
    if len(l['Actions']) > 0:
      act = l['Actions'][-1]
      return act['Type']
    else:
      return 'N/A'

  def determine_target(self, l, *args):
    if len(l['Actions']) > 0:
      act = l['Actions'][-1]
      if act['Type'] == 'forward':
        return ','.join([ARN(i['TargetGroupArn']).resource_id_first for i in act['ForwardConfig']['TargetGroups']])
      elif act['Type'] == 'redirect':
        r = act['RedirectConfig']
        proto = 'http(s)' if r['Protocol'] == '#{protocol}' else r['Protocol'].lower()
        proto_ports = []
        if proto in ['http', 'http(s)']:
          proto_ports.append('80')
        if proto in ['https', 'http(s)']:
          proto_ports.append('443')
        port = ':{0}'.format(r['Port']) if r['Port'] not in proto_ports else ''
        return '{4} {0}://{1}{2}{3}'.format(proto, r['Host'], port, r['Path'], '301' if r['StatusCode'] == 'HTTP_301' else '302')
    return ''

class ListenerActionDescriber(Describer):
  prefix = 'listener_action_browser'
  title = 'Listener Rule'

  def __init__(self, parent, alignment, dimensions, listener_entry, *args, **kwargs):
    self.rule_arn = listener_entry['arn']
    self.resource_key = 'elbv2'
    self.describe_method = 'describe_rules'
    self.describe_kwargs = {'RuleArns': [self.rule_arn]}
    self.object_path='.Rules[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.rule_arn

# Target Groups
class TargetGroupResourceLister(ResourceLister):
  prefix = 'target_group_list'
  title = 'Target Groups'

  def title_info(self):
    if self.rule is not None:
      return self.rule['arn']
    return None

  def __init__(self, *args, **kwargs):
    self.resource_key = 'elbv2'
    self.list_method = 'describe_target_groups'
    self.item_path = '.TargetGroups'
    if 'rule_entry' in kwargs:
      self.rule = kwargs['rule_entry']
      arns = []
      raw = self.rule.controller_data
      try:
        arns = [i['TargetGroupArn'] for i in raw['Actions'][-1]['ForwardConfig']['TargetGroups']]
        self.list_kwargs = {'TargetGroupArns': arns}
      except KeyError:
        self.rule = None
        Common.Session.set_message('Rule is not configured for forwarding.', Common.color('message_error'))
    else:
      self.rule = None
    self.column_paths = {
      'name': '.TargetGroupName',
      'protocol': '.Protocol',
      'port': '.Port',
      'target type': '.TargetType',
    }
    self.imported_column_sizes = {
      'name': 30,
      'protocol': 10,
      'port': 10,
      'target type': 10,
    }
    self.hidden_columns = {
      'arn': '.TargetGroupArn',
    }
    self.describe_command = TargetGroupDescriber.opener
    self.describe_selection_arg = 'tg_entry'
    #self.open_command = ListenerActionResourceLister.opener
    #self.open_selection_arg = 'listener'

    self.imported_column_order = ['name', 'protocol', 'port', 'target type']
    self.sort_column = 'name'
    self.primary_key = 'arn'
    super().__init__(*args, **kwargs)

class TargetGroupDescriber(Describer):
  prefix = 'tg_browser'
  title = 'Target Group'

  def __init__(self, parent, alignment, dimensions, tg_entry, *args, **kwargs):
    self.tg_arn = tg_entry['arn']
    self.tg_name = tg_entry['name']
    self.resource_key = 'elbv2'
    self.describe_method = 'describe_target_groups'
    self.describe_kwargs = {'TargetGroupArns': [self.tg_arn]}
    self.object_path='.TargetGroups[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.tg_name

# VPC
class VPCResourceLister(ResourceLister):
  prefix = 'vpc_list'
  title = 'VPCs'

  def __init__(self, *args, **kwargs):
    self.resource_key = 'ec2'
    self.list_method = 'describe_vpcs'
    self.item_path = '.Vpcs'
    self.column_paths = {
      'id': '.VpcId',
      'name': self.tag_finder_generator('Name'),
      'default': self.determine_default,
      'cidr': '.CidrBlock',
      'state': '.State',
    }
    self.imported_column_sizes = {
      'id': 30,
      'name': 30,
      'default': 3,
      'cidr': 18,
      'state': 9,
    }
    self.describe_command = VPCDescriber.opener
    self.describe_selection_arg = 'vpc_entry'
    self.additional_commands = {
      't': {
        'command': SubnetResourceLister.opener,
        'selection_arg': 'vpc',
        'tooltip': 'View Subnets',
      }
    }
    self.open_command = 't'

    self.imported_column_order = ['id', 'name', 'default', 'cidr', 'state']
    self.sort_column = 'id'
    self.primary_key = 'id'
    super().__init__(*args, **kwargs)

  def determine_default(self, vpc, *args):
    if vpc['IsDefault']:
      return '✓'
    return ''

class VPCDescriber(Describer):
  prefix = 'vpc_browser'
  title = 'VPC'

  def __init__(self, parent, alignment, dimensions, vpc_entry, *args, **kwargs):
    self.vpc_id = vpc_entry['id']
    self.resource_key = 'ec2'
    self.describe_method = 'describe_vpcs'
    self.describe_kwargs = {'VpcIds': [self.vpc_id]}
    self.object_path='.Vpcs[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.vpc_id

# Subnet
class SubnetResourceLister(ResourceLister):
  prefix = 'subnet_list'
  title = 'Subnets'

  def title_info(self):
    if self.vpc is not None:
      return self.vpc['id']
    elif self.db_subnet_group is not None:
      return self.db_subnet_group['name']
    return None

  def __init__(self, *args, **kwargs):
    self.resource_key = 'ec2'
    self.list_method = 'describe_subnets'
    self.item_path = '.Subnets'
    if 'vpc' in kwargs:
      self.vpc = kwargs['vpc']
      self.list_kwargs = {
        'Filters': [{
          'Name': 'vpc-id',
          'Values': [
            self.vpc['id'],
          ]
        }]
      }
    else:
      self.vpc = None
    if 'db_subnet_group' in kwargs:
      self.db_subnet_group = kwargs['db_subnet_group']
      self.list_kwargs = self.get_db_subnet_ids
    else:
      self.db_subnet_group = None
    self.column_paths = {
      'id': '.SubnetId',
      'name': self.tag_finder_generator('Name'),
      'vpc': '.VpcId',
      'cidr': '.CidrBlock',
      'AZ': '.AvailabilityZone',
      'public': self.determine_public,
    }
    self.hidden_columns = {
      'arn': '.SubnetArn',
    }
    self.imported_column_sizes = {
      'id': 30,
      'name': 30,
      'vpc': 30,
      'cidr': 18,
      'AZ': 20,
      'public': 3,
    }
    self.describe_command = SubnetDescriber.opener
    self.describe_selection_arg = 'subnet_entry'
    self.additional_commands = {
      't': {
        'command': RouteTableResourceLister.opener,
        'selection_arg': 'subnet',
        'tooltip': 'View Route Table',
      }
    }
    #self.open_command = RouteTableResourceLister.opener
    #self.open_selection_arg = 'subnet'

    self.imported_column_order = ['id', 'name', 'vpc', 'cidr', 'AZ', 'public']
    self.sort_column = 'id'
    self.primary_key = 'id'
    super().__init__(*args, **kwargs)

  def determine_public(self, subnet, *args):
    if subnet['MapPublicIpOnLaunch']:
      return '✓'
    return ''

  def get_db_subnet_ids(self, *args):
    dsg = Common.Session.service_provider('rds').describe_db_subnet_groups(DBSubnetGroupName=self.db_subnet_group.name)
    return {'SubnetIds': [s['SubnetIdentifier'] for s in dsg['DBSubnetGroups'][0]['Subnets']]}

class SubnetDescriber(Describer):
  prefix = 'subnet_browser'
  title = 'Subnet'

  def __init__(self, parent, alignment, dimensions, subnet_entry, *args, **kwargs):
    self.subnet_id = subnet_entry['id']
    self.resource_key = 'ec2'
    self.describe_method = 'describe_subnets'
    self.describe_kwargs = {'SubnetIds': [self.subnet_id]}
    self.object_path='.Subnets[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.subnet_id

# RouteTable
class RouteTableResourceLister(ResourceLister):
  prefix = 'route_table_list'
  title = 'Route Tables'

  def title_info(self):
    if self.subnet is not None:
      return self.subnet['id']
    return None

  def __init__(self, *args, **kwargs):
    self.resource_key = 'ec2'
    self.list_method = 'describe_route_tables'
    self.item_path = '.RouteTables'
    if 'subnet' in kwargs:
      self.subnet = kwargs['subnet']
      self.list_kwargs = {
        'Filters': [{
          'Name': 'association.subnet-id',
          'Values': [
            self.subnet['id'],
          ]
        }]
      }
    else:
      self.subnet = None
    self.column_paths = {
      'id': '.RouteTableId',
      'name': self.tag_finder_generator('Name'),
      'vpc': '.VpcId',
      'subnet': self.determine_subnet_association,
    }
    self.imported_column_sizes = {
      'id': 30,
      'name': 30,
      'vpc': 30,
      'subnet': 30,
    }
    self.describe_command = RouteTableDescriber.opener
    self.describe_selection_arg = 'route_table_entry'
    self.open_command = RouteResourceLister.opener
    self.open_selection_arg = 'route_table'

    self.imported_column_order = ['id', 'name', 'vpc', 'subnet']
    self.sort_column = 'id'
    self.primary_key = 'id'
    super().__init__(*args, **kwargs)

  def determine_subnet_association(self, rt, *args):
    if 'Associations' not in rt or len(rt['Associations']) == 0:
      return '<none>'
    if len(rt['Associations']) > 1:
      return '<multiple>'
    if 'SubnetId' in rt['Associations'][0]:
      return rt['Associations'][0]['SubnetId']
    else:
      return '<VPC default>'

class RouteTableDescriber(Describer):
  prefix = 'route_table_browser'
  title = 'Route Table'

  def __init__(self, parent, alignment, dimensions, route_table_entry, *args, **kwargs):
    self.route_table_id = route_table_entry['id']
    self.resource_key = 'ec2'
    self.describe_method = 'describe_route_tables'
    self.describe_kwargs = {'RouteTableIds': [self.route_table_id]}
    self.object_path='.RouteTables[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.route_table_id

# Routes
class RouteResourceLister(ResourceLister):
  prefix = 'routee_list'
  title = 'Routes'

  def title_info(self):
    if self.route_table is not None:
      return self.route_table['id']
    return None

  def __init__(self, *args, **kwargs):
    self.resource_key = 'ec2'
    self.list_method = 'describe_route_tables'
    self.item_path = '[.RouteTables[] as $rt | $rt.Routes[] as $r | $r | .RouteTableId = $rt.RouteTableId]'
    if 'route_table' in kwargs:
      self.route_table = kwargs['route_table']
      self.list_kwargs = {
        'RouteTableIds': [self.route_table['id']]
      }
    else:
      self.route_table = None
    self.column_paths = {
      'route table': '.RouteTableId',
      'gateway type': self.determine_gateway_type,
      'gateway': self.determine_gateway,
      'destination': '.DestinationCidrBlock',
      'state': '.State',
    }
    self.hidden_columns = {
      'name': self.empty,
    }
    self.imported_column_sizes = {
      'route table': 30,
      'gateway type': 20,
      'gateway': 30,
      'destination': 30,
      'state': 10,
    }

    self.imported_column_order = ['route table', 'gateway type', 'gateway', 'destination', 'state']
    self.sort_column = 'route table'
    self.primary_key = None
    super().__init__(*args, **kwargs)

    self.add_hotkey('d', self.generic_describe, 'Describe')
    self.add_hotkey('KEY_ENTER', self.generic_describe, 'Describe')

  def generic_describe(self, entry):
    if self.selection is not None:
      Common.Session.push_frame(GenericDescriber.opener(**{
        'describing': 'Route in route table {0}'.format(self.selection['route table']),
        'content': json.dumps(self.selection.controller_data, sort_keys=True, indent=2),
        'pushed': True,
      }))

  def determine_gateway_type(self, entry):
    if 'NatGatewayId' in entry:
      return 'NAT'
    elif 'InstanceId' in entry:
      return 'Instance'
    elif 'TransitGatewayId' in entry:
      return 'Transit'
    elif 'LocalGatewayId' in entry:
      return 'Local'
    elif 'CarrierGatewayId' in entry:
      return 'Carrier'
    elif 'VpcPeeringConnectionId' in entry:
      return 'VPC Peering'
    elif 'EgressOnlyInternetGatewayId' in entry:
      return 'Egress-Only'
    elif entry['GatewayId'] == 'local':
      return 'VPC-Local'
    else:
      return 'Internet'

  def determine_gateway(self, entry):
    if 'NatGatewayId' in entry:
      return entry['NatGatewayId']
    elif 'InstanceId' in entry:
      return entry['InstanceId']
    elif 'TransitGatewayId' in entry:
      return entry['TransitGatewayId']
    elif 'LocalGatewayId' in entry:
      return entry['LocalGatewayId']
    elif 'CarrierGatewayId' in entry:
      return entry['CarrierGatewayId']
    elif 'VpcPeeringConnectionId' in entry:
      return entry['VpcPeeringConnectionId']
    elif 'EgressOnlyInternetGatewayId' in entry:
      return entry['EgressOnlyInternetGatewayId']
    else:
      return entry['GatewayId']

# DBSubnetGroups
class DBSubnetGroupResourceLister(ResourceLister):
  prefix = 'db_subnet_group_list'
  title = 'DB Subnet Groups'

  def __init__(self, *args, **kwargs):
    self.resource_key = 'rds'
    self.list_method = 'describe_db_subnet_groups'
    self.item_path = '.DBSubnetGroups'
    self.column_paths = {
      'name': '.DBSubnetGroupName',
      'vpc': '.VpcId',
      'status': '.SubnetGroupStatus'
    }
    self.hidden_columns = {
      'arn': '.DBSubnetGroupArn',
    }
    self.imported_column_sizes = {
      'name': 30,
      'vpc': 30,
      'status': 30,
    }
    self.describe_command = DBSubnetGroupDescriber.opener
    self.describe_selection_arg = 'dsg_entry'
    self.open_command = SubnetResourceLister.opener
    self.open_selection_arg = 'db_subnet_group'
    self.primary_key = 'name'

    self.imported_column_order = ['name', 'vpc', 'status']
    self.sort_column = 'name'
    super().__init__(*args, **kwargs)

class DBSubnetGroupDescriber(Describer):
  prefix = 'subnet_browser'
  title = 'Subnet'

  def __init__(self, parent, alignment, dimensions, dsg_entry, *args, **kwargs):
    self.dsg_name = dsg_entry['name']
    self.resource_key = 'rds'
    self.describe_method = 'describe_db_subnet_groups'
    self.describe_kwargs = {'DBSubnetGroupName': self.dsg_name}
    self.object_path='.DBSubnetGroups[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.dsg_name

# S3
class S3ResourceLister(ResourceLister):
  prefix = 's3_list'
  title = 'S3 Buckets'

  def __init__(self, *args, **kwargs):
    self.resource_key = 's3'
    self.list_method = 'list_buckets'
    self.item_path = '.Buckets'
    self.column_paths = {
      'name': '.Name',
      'location': self.determine_location,
    }
    self.imported_column_sizes = {
      'name': 60,
      'location': 20,
    }
    self.describe_command = S3Describer.opener
    self.describe_selection_arg = 'bucket'
    self.open_command = S3ObjectLister.opener
    self.open_selection_arg = 'bucket'
    self.primary_key = 'name'

    self.imported_column_order = ['name', 'location']
    self.sort_column = 'name'
    super().__init__(*args, **kwargs)

  def determine_location(self, entry):
    loc_resp = Common.Session.service_provider('s3').get_bucket_location(Bucket=entry['Name'])
    return loc_resp['LocationConstraint']

class S3Describer(Describer):
  prefix = 's3_browser'
  title = 'S3 Bucket'

  def __init__(self, parent, alignment, dimensions, bucket, *args, **kwargs):
    self.bucket = bucket['name']
    self.resource_key = 'rds'
    self.describe_method = 'get_bucket_policy'
    self.describe_kwargs = {'Bucket': self.bucket}
    self.object_path='.'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.bucket

class CancelDownload(Exception):
  pass

class S3ObjectLister(ResourceLister):
  prefix = 's3_object_list'
  title = 'S3 Browser'

  def title_info(self):
    if self.path is None:
      return self.bucket
    else:
      return '{0}/{1}'.format(self.bucket, self.path)

  def __init__(self, *args, bucket, path=None, **kwargs):
    self.icons = {
      'folder': '🗀',
      'default': '🗈',
      'ext.txt': '🖹',
      'ext.png': '🖻',
      'ext.jpg': '🖻',
      'ext.gif': '🖻',
      'ext.jpeg': '🖻',
      'ext.svg': '🖻',
      'ext.doc': '🖺',
      'ext.docx': '🖺',
      'ext.xls': '🖺',
      'ext.xlsx': '🖺',
      'ext.ppt': '🖺',
      'ext.pptx': '🖺',
    }

    self.resource_key = 's3'
    self.list_method = 'list_objects'
    if isinstance(bucket, ListEntry):
      self.bucket = bucket['name']
    else:
      self.bucket = bucket
    self.path = path
    self.list_kwargs = {'Bucket': self.bucket, 'MaxKeys': 100, 'Delimiter': '/'}
    self.next_marker = 'NextMarker'
    self.next_marker_arg = 'Marker'
    if self.path is not None:
      self.list_kwargs['Prefix'] = self.path
    self.item_path = '.Contents + .CommonPrefixes'
    self.column_paths = {
      'icon': self.determine_icon,
      'name': self.determine_name,
      'size': self.determine_size,
    }
    self.hidden_columns = {
      'is_dir': self.determine_is_dir,
      'size_in_bytes': '.Size',
      'bucket_prefixed_path': self.determine_bucket_prefixed_path,
    }
    self.imported_column_sizes = {
      'icon': 1,
      'name': 150,
      'size': 20,
    }
    self.imported_column_order = ['icon', 'name', 'size']
    self.sort_column = 'name'
    self.additional_commands = {
      'd': {
        'command': self.download_selection,
        'selection_arg': 'file',
        'tooltip': 'Download',
      },
      'v': {
        'command': self.view_selection,
        'selection_arg': 'file',
        'tooltip': 'View Contents',
      }
    }
    self.open_command = S3ObjectLister.opener
    self.open_selection_arg = 'path'
    super().__init__(*args, **kwargs)
    self.primary_key = 'bucket_prefixed_path'
    self.add_hotkey(ControlCodes.D, self.empty, 'Cancel download')

  def determine_bucket_prefixed_path(self, entry, *args):
    return '{0}/{1}'.format(self.bucket, entry['Key'] if 'Key' in entry else entry['Prefix'])

  def determine_name(self, entry, *args):
    if 'Prefix' in entry:
      return entry['Prefix'].strip('/').split('/')[-1]
    return entry['Key'].split('/')[-1]

  def determine_is_dir(self, entry, *args):
    return '/' if 'Prefix' in entry else ''

  def determine_size(self, entry, *args):
    if 'Prefix' in entry:
      return ''
    b_prefix = ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Ei']
    b_idx = 0
    s = float(entry['Size'])
    while s >= 1024:
      b_idx += 1
      s /= 1024
      if b_idx == len(b_prefix) - 1:
        break
    return '{0:.2f} {1}B'.format(s, b_prefix[b_idx])

  def determine_icon(self, entry, *args):
    if 'Prefix' in entry:
      return self.icons['folder']
    ext = entry['Key'].split('/')[-1].split('.')[-1]
    ext_key = 'ext.{0}'.format(ext)
    if ext_key in self.icons:
      return self.icons[ext_key]
    return self.icons['default']

  def open(self, *args):
    if self.open_command is not None and self.selection is not None and self.selection['is_dir'] == '/':
      subpath = self.get_selection_path()
      self.command(self.open_command, {self.open_selection_arg: subpath, 'bucket': self.bucket, 'pushed': True})

  def get_selection_path(self):
    if self.selection is not None:
      if self.path is None:
        return '{0}{1}'.format(self.selection['name'], self.selection['is_dir'])
      else:
        return '{0}{1}{2}'.format(self.path, self.selection['name'], self.selection['is_dir'])
    return None

  def get_cache_name(self):
    return '{0}/{1}'.format(self.bucket, self.get_selection_path()).replace('/', '--')

  def cache_fetch(self, obj, *args, **kwargs):
    if self.selection is not None:
      sp = self.get_selection_path()
      obj_size = float(self.selection['size_in_bytes'])
      downloaded = 0
      def fn(chunk):
        nonlocal downloaded
        downloaded += chunk
        perc = float(downloaded) / obj_size
        key = Common.Session.ui.check_one_key()
        if key == ControlCodes.C:
          raise KeyboardInterrupt
        elif key == ControlCodes.D:
          raise CancelDownload()
        Common.Session.ui.progress_bar_paint(perc)
      Common.Session.service_provider('s3').download_file(Bucket=self.bucket, Key=sp, Filename=obj, Callback=fn)
      try:
        with open(obj, 'r') as f:
          return f.read()
      except UnicodeDecodeError:
        with open(obj, 'rb') as f:
          return f.read()

  def download_selection(self, *args, **kwargs):
    if self.selection is not None:
      if self.selection['is_dir'] == '/':
        Common.Session.set_message('Cannot download directory as file.', Common.color('message_info'))
        return
      path = Path.home() / 'Downloads' / 'awsc'
      path.mkdir(parents=True, exist_ok=True)
      try:
        data = Common.Session.ui.filecache(self.get_cache_name(), self.cache_fetch)
      except CancelDownload:
        Common.Session.set_message('Download cancelled', Common.color('message_info'))
        return None
      fpath = path / self.selection['name']
      mode = 'w'
      if isinstance(data, bytes):
        mode = 'wb'
      with fpath.open(mode) as f:
        f.write(data)
      Common.Session.set_message('Downloaded file to {0}'.format(str(fpath.resolve())), Common.color('message_success'))
    return None

  def view_selection(self, *args, **kwargs):
    if self.selection is not None:
      if self.selection['is_dir'] == '/':
        Common.Session.set_message('Cannot display directory as text file.', Common.color('message_info'))
        return None
      try:
        data = Common.Session.ui.filecache(self.get_cache_name(), self.cache_fetch)
      except CancelDownload:
        Common.Session.set_message('Download cancelled', Common.color('message_info'))
        return None
      if isinstance(data, bytes):
        data = '<binary>'
      return GenericDescriber.opener(**{
        'describing': 'File: {0}'.format(self.get_selection_path()),
        'content': data,
        'pushed': True,
      })
    return None
