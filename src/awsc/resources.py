"""
Module which imports all the resource controls and registers an init hook to register the controls with the session.
"""
from .base_control import Describer, GenericDescriber, ResourceLister
from .common import Common
from .resource_ami import *
from .resource_asg import *
from .resource_beanstalk import *
from .resource_cfn import *
from .resource_cloudwatch import *
from .resource_dsg import *
from .resource_ebs import *
from .resource_ec2 import *
from .resource_ec2_class import *
from .resource_iam import *
from .resource_iam_group import *
from .resource_iam_instance_profile import *
from .resource_iam_policy import *
from .resource_iam_role import *
from .resource_iam_user import *
from .resource_keypair import *
from .resource_lb import *
from .resource_lc import *
from .resource_listener import *
from .resource_r53 import *
from .resource_rds import *
from .resource_routing import *
from .resource_s3 import *
from .resource_sg import *
from .resource_sqs import *
from .resource_subnet import *
from .resource_tg import *
from .resource_vpc import *

Common.run_on_init(ResourceLister.register)
Common.run_on_init(Describer.register)
Common.run_on_init(GenericDescriber.register)
