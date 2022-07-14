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

class MetricLister(ResourceLister):
  prefix = 'metric_list'
  title = 'Metrics'

  def title_info(self):
    if self.dimension is not None:
      return '{0}={1}'.format(self.dimensions[0], self.dimension[1])
    return None

  def __init__(self, *args, metric_namespace=None, metric_name=None, dimension=None, **kwargs):
    self.resource_key = 'cloudwatch'
    self.list_method = 'list_metrics'
    self.item_path = '.Metrics'
    self.column_paths = {
      'namespace': '.Namespace',
      'name': '.MetricName',
    }
    self.imported_column_sizes = {
      'namespace': 16,
      'name': 64,
    }
    self.hidden_columns = {
      'dimension': self.add_dimension,
    }
    self.dimension = dimension
    self.list_kwargs = {}
    if metric_namespace is not None:
      self.list_kwargs['Namespace'] = metric_namespace
    if metric_name is not None:
      self.list_kwargs['MetricName'] = metric_name
    if dimension is not None:
      self.list_kwargs['Dimensions'] = [{'Name': dimension[0], 'Value': dimension[1]}]
    self.primary_key = 'name'
    self.sort_column = 'name'
    self.open_command = MetricViewer.opener
    self.open_selection_arg = 'metric'
    super().__init__(*args, **kwargs)

  def add_dimension(self, entry):
    if self.dimension is not None:
      return '{0}={1}'.format(self.dimension[0], self.dimension[1])
    return ''

class MetricViewer(BaseChart):
  prefix = 'metric_view'
  title = 'Metrics'

  def title_info(self):
    return '{0} {1}'.format(self.metric_dimension['Value'], self.metric_name)

  def __init__(self, *args, metric=None, **kwargs):
    super().__init__(*args, **kwargs)
    self.metric_name = metric['name']
    self.metric_namespace = metric['namespace']
    d = metric['dimension'].split('=')
    self.metric_dimension = {
      'Name': d[0],
      'Value': '='.join(d[1:]),
    }
    self.load_data()

  def load_data(self):
    data = Common.Session.service_provider('cloudwatch').get_metric_data(MetricDataQueries=[{
        'Id': 'metric',
        'MetricStat': {
          'Metric': {
            'Namespace': self.metric_namespace,
            'MetricName': self.metric_name,
            'Dimensions': [self.metric_dimension],
          },
          'Period': 300,
          'Stat': 'Average',
        },
      }],
      StartTime=datetime.datetime.now() - datetime.timedelta(hours=24),
      EndTime=datetime.datetime.now(),
    )
    for idx in range(len(data['MetricDataResults'][0]['Timestamps'])):
      ts = data['MetricDataResults'][0]['Timestamps'][idx]
      val = data['MetricDataResults'][0]['Values'][idx]
      self.add_datapoint(ts, val)
