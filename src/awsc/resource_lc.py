"""
Module for Launch Configuration resources.
"""
from .base_control import Describer, ResourceLister, ResourceRefByClass


class LCDescriber(Describer):
    """
    Describer control for autoscaling launch configurations.
    """

    prefix = "lc_browser"
    title = "Launch Configuration"

    def __init__(self, *args, **kwargs):
        self.resource_key = "autoscaling"
        self.describe_method = "describe_launch_configurations"
        self.describe_kwarg_name = "LaunchConfigurationNames"
        self.describe_kwarg_is_list = True
        self.object_path = ".LaunchConfigurations[0]"
        super().__init__(*args, **kwargs)


class LCResourceLister(ResourceLister):
    """
    Lister control for autoscaling launch configurations.
    """

    prefix = "lc_list"
    title = "Launch Configurations"
    command_palette = ["lc", "launchconfiguration"]

    resource_type = "launch configuration"
    main_provider = "autoscaling"
    category = "Autoscaling"
    subcategory = "Launch Configuration"
    list_method = "describe_launch_configurations"
    item_path = ".LaunchConfigurations"
    columns = {
        "name": {
            "path": ".LaunchConfigurationName",
            "size": 30,
            "weight": 0,
            "sort_weight": 0,
        },
        "image id": {"path": ".ImageId", "size": 20, "weight": 1},
        "instance type": {
            "path": ".InstanceType",
            "size": 20,
            "weight": 2,
        },
    }
    describe_command = LCDescriber.opener
    open_command = ResourceRefByClass("ASGResourceLister")
    open_selection_arg = "lc"
