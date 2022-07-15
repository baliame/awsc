import datetime
import json
import subprocess
import time
from pathlib import Path

import botocore
import jq

from .arn import ARN
from .base_control import (DeleteResourceDialog, Describer,
                           DialogFieldResourceListSelector, GenericDescriber,
                           MultiLister, NoResults, ResourceLister,
                           SingleRelationLister)
from .common import BaseChart, Common, SessionAwareDialog
from .ssh import SSHList
from .termui.alignment import CenterAnchor, Dimension
from .termui.control import Border
from .termui.dialog import (DialogControl, DialogFieldButton,
                            DialogFieldCheckbox, DialogFieldLabel,
                            DialogFieldText)
from .termui.list_control import ListEntry
from .termui.ui import ControlCodes


class LCResourceLister(ResourceLister):
    prefix = "lc_list"
    title = "Launch Configurations"
    command_palette = ["lc", "launchconfiguration"]

    def __init__(self, *args, **kwargs):
        from .resource_asg import ASGResourceLister

        self.resource_key = "autoscaling"
        self.list_method = "describe_launch_configurations"
        self.item_path = ".LaunchConfigurations"
        self.column_paths = {
            "name": ".LaunchConfigurationName",
            "image id": ".ImageId",
            "instance type": ".InstanceType",
        }
        self.imported_column_sizes = {
            "name": 30,
            "image id": 20,
            "instance type": 20,
        }
        self.describe_command = LCDescriber.opener
        self.open_command = ASGResourceLister.opener
        self.open_selection_arg = "lc"

        self.imported_column_order = ["name", "image id", "instance type"]
        self.sort_column = "name"
        super().__init__(*args, **kwargs)


class LCDescriber(Describer):
    prefix = "lc_browser"
    title = "Launch Configuration"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "autoscaling"
        self.describe_method = "describe_launch_configurations"
        self.describe_kwarg_name = "LaunchConfigurationNames"
        self.describe_kwarg_is_list = True
        self.object_path = ".LaunchConfigurations[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
