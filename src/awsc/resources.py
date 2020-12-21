from .resource_lister import ResourceLister, Describer, MultiLister
from .common import Common
from .termui.dialog import DialogControl, DialogFieldText
from .termui.alignment import CenterAnchor, Dimension
from .termui.control import Border
from .termui.list_control import ListEntry
import subprocess
from pathlib import Path
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
      'name': self.determine_name,
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
    self.describe_command = EC2Describer.opener
    self.describe_selection_arg = 'instance_entry'
    self.imported_column_order = ['instance id', 'name', 'type', 'vpc', 'public ip', 'key name', 'state']
    self.sort_column = 'instance id'
    super().__init__(*args, **kwargs)
    self.add_hotkey('s', self.ssh, 'Open SSH')

  def determine_name(self, instance):
    for tag in instance['Tags']:
      if tag['Key'] == 'Name':
        return tag['Value']
    return ''

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
      'name': self.determine_name,
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
    super().__init__(*args, **kwargs)
    self.add_hotkey('s', self.db_client, 'Open command line')

  def determine_name(self, instance):
    for tag in instance['TagList']:
      if tag['Key'] == 'Name':
        return tag['Value']
    return ''

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
          'name': self.determine_ec2_name,
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
          'name': self.determine_rds_name,
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
    ]
    super().__init__(*args, **kwargs)

  def comparer_generator(self, cfn_type, physical_id_path):
    def fn(raw_item):
      phys_id = jq.compile(physical_id_path).input(raw_item).first()
      if '{0}|{1}'.format(cfn_type, phys_id) in self.stack_res_list:
        return self.compare_value
      return 'False'
    return fn

  def async_inner(self, *args, fn, clear=False, **kwargs):
    stop = False
    rl = None
    self.stack_res_list = []
    while not stop:
      rargs = {'StackName': self.orig_compare_value['name']}
      if rl is not None and 'NextToken' in rl and rl['NextToken'] is not None:
        rargs['NextToken'] = rl['NextToken']
      rl = Common.Session.service_provider('cloudformation').list_stack_resources(**rargs)
      if 'NextToken' not in rl or rl['NextToken'] is None:
        stop = True
      for item in rl['StackResourceSummaries']:
        self.stack_res_list.append('{0}|{1}'.format(item['ResourceType'], item['PhysicalResourceId']))
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
