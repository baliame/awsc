from .base_control import ResourceLister
from .common import Common

Common.run_on_init(ResourceLister.register)
