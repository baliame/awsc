"""
AWS Autoscaling Group resource controls.
"""
from .base_control import Describer, ResourceLister
from .common import Common, SessionAwareDialog
from .termui.control import Border
from .termui.dialog import DialogFieldCheckbox, DialogFieldLabel, DialogFieldText
from .termui.ui import ControlCodes


def _asg_determine_launch_info(asg):
    """
    Column callback for determining the name of the launch configuration or launch template associated with an autoscaling group.

    Parameters
    ----------
    asg : dict
        Partial raw JSON response from the AWS API, one autoscaling group object.

    Returns
    -------
    str
        The name of the launch configuration or launch template associated with the ASG, or empty if not found.
    """
    if "LaunchConfigurationName" in asg and bool(asg["LaunchConfigurationName"]):
        return asg["LaunchConfigurationName"]
    if "LaunchTemplate" in asg:
        return asg["LaunchTemplate"]["LaunchTemplateName"]
    return ""


def _asg_determine_instance_count(asg):
    """
    Column callback for determining the number of healthy and total instances in an autoscaling group.

    Parameters
    ----------
    asg : dict
        Partial raw JSON response from the AWS API, one autoscaling group object.

    Returns
    -------
    str
        The number of healthy and total instances in the group in the format of healthy/total.
    """
    healthy = len([h for h in asg["Instances"] if h["HealthStatus"] == "Healthy"])
    total = len(asg["Instances"])
    return f"{healthy}/{total}"


class ASGDescriber(Describer):
    """
    Describer control for Autoscaling Group resources.
    """

    prefix = "asg_browser"
    title = "Autoscaling Group"

    def __init__(self, *args, **kwargs):
        self.resource_key = "autoscaling"
        self.describe_method = "describe_auto_scaling_groups"
        self.describe_kwarg_name = "AutoScalingGroupNames"
        self.describe_kwarg_is_list = True
        self.object_path = ".AutoScalingGroups[0]"
        super().__init__(*args, **kwargs)


class ASGResourceLister(ResourceLister):
    """
    Lister control for Autoscaling Group resources.

    Attributes
    ----------
    launch_config : awsc.termui.list_control.ListEntry
        List ASGs in the context of this launch configuration.
    """

    prefix = "asg_list"
    title = "Autoscaling Groups"
    command_palette = ["asg", "autoscaling"]

    resource_type = "autoscaling group"
    main_provider = "autoscaling"
    category = "Autoscaling"
    subcategory = "Autoscaling Group"
    list_method = "describe_auto_scaling_groups"
    item_path = ".AutoScalingGroups"
    columns = {
        "name": {
            "path": ".AutoScalingGroupName",
            "size": 30,
            "weight": 0,
            "sort_weight": 0,
        },
        "template": {
            "path": _asg_determine_launch_info,
            "size": 30,
            "weight": 1,
        },
        "current": {
            "path": _asg_determine_instance_count,
            "size": 10,
            "weight": 2,
        },
        "min": {"path": ".MinSize", "size": 10, "weight": 3},
        "desired": {"path": ".DesiredCapacity", "size": 10, "weight": 4},
        "max": {"path": ".MaxSize", "size": 10, "weight": 5},
        "launch config": {"path": ".LaunchConfigurationName", "hidden": True},
        "arn": {"path": ".AutoScalingGroupARN", "hidden": True},
    }

    describe_command = ASGDescriber.opener
    open_command = "i"
    primary_key = "name"

    def title_info(self):
        return (
            None
            if self.launch_config is None
            else f"LaunchConfiguration: {self.launch_config['name']}"
        )

    def matches(self, list_entry, *args):
        if self.launch_config is not None:
            if list_entry["launch config"] != self.launch_config["name"]:
                return False
        return super().matches(list_entry, *args)

    def __init__(self, *args, lc=None, **kwargs):
        self.launch_config = lc
        super().__init__(*args, **kwargs)

    @ResourceLister.Autohotkey(ControlCodes.S, tooltip="Scale", is_validated=True)
    def scale_group(self, _):
        """
        Hotkey callback for resize action on autoscaling group.
        """
        ASGScaleDialog.opener(
            caller=self,
        )


class ASGScaleDialog(SessionAwareDialog):
    """
    Dialog for scaling autoscaling groups.

    Attributes
    ----------
    asg_entry : awsc.termui.list_control.ListEntry
        The autoscaling group being scaled.
    error_label : awsc.termui.dialog.DialogFieldLabel
        An error display field, for displaying validation errors.
    desired_capacity_field : awsc.termui.dialog.DialogFieldText
        Textfield for inputting the new desired capacity of the group.
    adjust_limits_field : awsc.termui.dialog.DialogFieldCheckbox
        If checked, desired capacity may exceed bounds set by min/max size, as those will be automatically expanded to fit the new desired
        capacity.
    caller : awsc.termui.control.Control
        The parent control opening this dialog.
    """

    def __init__(self, *args, caller=None, **kwargs):
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            "Scale autoscaling group",
            Common.color("modal_dialog_border_title"),
            caller.selection["name"],
            Common.color("modal_dialog_border_title_info"),
        )
        self.asg_entry = caller.selection
        super().__init__(caller=caller, *args, **kwargs)
        self.desired_capacity_field = DialogFieldText(
            "Desired capacity:",
            text=str(self.asg_entry["desired"]),
            label_min=16,
            color=Common.color("modal_dialog_textfield"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
            label_color=Common.color("modal_dialog_textfield_label"),
            accepted_inputs="0123456789",
        )
        self.add_field(self.desired_capacity_field)
        self.add_field(DialogFieldLabel(""))
        self.adjust_limits_field = DialogFieldCheckbox(
            "Adjust min/max capacity if required",
            checked=True,
            color=Common.color("modal_dialog_textfield_label"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
        )
        self.add_field(self.adjust_limits_field)
        self.caller = caller

    def accept_and_close(self):
        if self.desired_capacity_field.text == "":
            self.error_label.text = "Desired capacity cannot be blank."
            return

        b3s = Common.Session.service_provider("autoscaling")
        asg = b3s.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_entry["name"]]
        )["AutoScalingGroups"][0]
        des = int(self.desired_capacity_field.text)

        if (
            des < asg["MinSize"] or des > asg["MaxSize"]
        ) and not self.adjust_limits_field.checked:
            self.error_label.text = f"Desired capacity is out of min-max range of {asg['MinSize']}-{asg['MaxSize']}"
            return

        nmin = min(des, asg["MinSize"])
        nmax = max(des, asg["MaxSize"])

        b3s.update_auto_scaling_group(
            AutoScalingGroupName=self.asg_entry["name"],
            DesiredCapacity=des,
            MinSize=nmin,
            MaxSize=nmax,
        )
        super().accept_and_close()

    def close(self):
        if self.caller is not None:
            self.caller.refresh_data()
        super().close()
