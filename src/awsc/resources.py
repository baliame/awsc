from .resource_lister import ResourceLister, Describer

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
    }
    self.imported_column_sizes = {
      'instance id': 11,
      'name': 30,
      'type': 10,
      'vpc': 15,
      'public ip': 15,
      'key name': 30,
    }
    self.describe_command = EC2Describer.opener
    self.describe_selection_arg = 'instance_entry'
    self.imported_column_order = ['instance id', 'name', 'type', 'vpc', 'public ip', 'key name']
    self.sort_column = 'instance id'
    super().__init__(*args, **kwargs)

  def determine_name(self, instance):
    for tag in instance['Tags']:
      if tag['Key'] == 'Name':
        return tag['Value']
    return ''

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

# ASG

from .resource_lister import ResourceLister, Describer

class ASGResourceLister(ResourceLister):
  prefix = 'asg_list'
  title = 'Autoscaling Groups'

  def __init__(self, *args, **kwargs):
    self.resource_key = 'autoscaling'
    self.list_method = 'describe_auto_scaling_groups'
    self.item_path = '.AutoScalingGroups'
    self.column_paths = {
      'name': '.AutoScalingGroupName',
      'launch config/template': self.determine_launch_info,
      'current': self.determine_instance_count,
      'min': '.MinSize',
      'desired': '.DesiredCapacity',
      'max': '.MaxSize',
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
    return str(len(asg['Instances']))

class ASGDescriber(Describer):
  prefix = 'asg_browser'
  title = 'Autoscaling Group'

  def __init__(self, parent, alignment, dimensions, instance_entry, *args, **kwargs):
    self.instance_id = instance_entry['instance id']
    self.resource_key = 'ec2'
    self.describe_method = 'describe_instances'
    self.describe_kwargs = {'InstanceIds': [self.instance_id]}
    self.object_path='.Reservations[0].Instances[0]'
    super().__init__(parent, alignment, dimensions, *args, **kwargs)

  def title_info(self):
    return self.instance_id
