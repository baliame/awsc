import boto3
from .common import Common
from botocore import config as botoconf
from botocore import exceptions

class AWS:
  def __init__(self):
    Common.Session.context_update_hooks.append(self.idcaller)
    self.idcaller()

  def conf(self):
    return botoconf.Config(
      region_name = Common.Session.region,
      signature_version = 'v4',
    )

  def s3conf(self):
    return botoconf.Config(
      region_name = Common.Session.region,
      signature_version = 's3v4',
    )

  def env_session(self):
    return boto3.Session()

  def __call__(self, service, keys=None):
    if service == 's3':
      config = self.s3conf()
    else:
      config = self.conf()
    return boto3.client(
      service,
      aws_access_key_id=keys['access'] if keys is not None else Common.Configuration.keystore[Common.Session.context]['access'],
      aws_secret_access_key=keys['secret'] if keys is not None else Common.Configuration.keystore[Common.Session.context]['secret'],
      config=config,
    )

  def whoami(self, keys=None):
    return self('sts', keys).get_caller_identity()

  def list_regions(self):
    return [region['RegionName'] for region in self('ec2').describe_regions(AllRegions=True)['Regions']]

  def idcaller(self):
    try:
      w = self.whoami()
      try:
        del(Common.Session.info_display.special_colors['Account'])
        del(Common.Session.info_display.special_colors['UserId'])
      except KeyError:
        pass
      Common.Session.info_display['UserId'] = w['UserId']
      Common.Session.info_display['Account'] = w['Account']
    except (exceptions.ClientError, KeyError) as e:
      Common.Session.info_display.special_colors['UserId'] = Common.color('error')
      Common.Session.info_display.special_colors['Account'] = Common.color('error')
      Common.Session.info_display['UserId'] = 'ERROR'
      Common.Session.info_display['Account'] = 'ERROR'
      Common.Session.ui.log('ERROR: From AWS API: {0}'.format(e))

