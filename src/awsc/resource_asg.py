from .base_control import Describer, ResourceLister
from .common import Common, SessionAwareDialog
from .termui.alignment import CenterAnchor, Dimension
from .termui.control import Border
from .termui.dialog import DialogFieldCheckbox, DialogFieldLabel, DialogFieldText
from .termui.ui import ControlCodes


class ASGResourceLister(ResourceLister):
    prefix = "asg_list"
    title = "Autoscaling Groups"
    command_palette = ["asg", "autoscaling"]

    def title_info(self):
        return self.title_info_data

    def matches(self, list_entry, *args):
        if self.launch_config is not None:
            if list_entry["launch config"] != self.launch_config["name"]:
                return False
        return super().matches(list_entry, *args)

    def __init__(self, *args, **kwargs):
        from .resource_ec2 import EC2ResourceLister

        self.resource_key = "autoscaling"
        self.list_method = "describe_auto_scaling_groups"
        self.title_info_data = None
        self.launch_config = None
        if "lc" in kwargs:
            launch_config = kwargs["lc"]
            self.title_info_data = f"LaunchConfiguration: {launch_config['name']}"
            self.launch_config = launch_config

        self.item_path = ".AutoScalingGroups"
        self.column_paths = {
            "name": ".AutoScalingGroupName",
            "launch config/template": self.determine_launch_info,
            "current": self.determine_instance_count,
            "min": ".MinSize",
            "desired": ".DesiredCapacity",
            "max": ".MaxSize",
        }
        self.hidden_columns = {
            "launch config": ".LaunchConfigurationName",
            "arn": ".AutoScalingGroupARN",
        }
        self.imported_column_sizes = {
            "name": 30,
            "launch config/template": 30,
            "current": 10,
            "min": 10,
            "desired": 10,
            "max": 10,
        }
        self.describe_command = ASGDescriber.opener
        self.open_command = EC2ResourceLister.opener
        self.open_selection_arg = "asg"
        self.imported_column_order = [
            "name",
            "launch config/template",
            "current",
            "min",
            "desired",
            "max",
        ]

        self.sort_column = "name"
        self.primary_key = "name"
        super().__init__(*args, **kwargs)
        self.add_hotkey(ControlCodes.S, self.scale_group, "Scale")

    def determine_launch_info(self, asg):
        if "LaunchConfigurationName" in asg and bool(asg["LaunchConfigurationName"]):
            return asg["LaunchConfigurationName"]
        if "LaunchTemplate" in asg:
            return asg["LaunchTemplate"]["LaunchTemplateName"]
        return ""

    def determine_instance_count(self, asg):
        healthy = len([h for h in asg["Instances"] if h["HealthStatus"] == "Healthy"])
        total = len(asg["Instances"])
        return f"{healthy}/{total}"

    def scale_group(self, _):
        if self.selection is not None:
            ASGScaleDialog(
                self.parent,
                CenterAnchor(0, 0),
                Dimension("80%|40", "20"),
                caller=self,
                weight=-500,
            )


class ASGScaleDialog(SessionAwareDialog):
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
        self.error_label = DialogFieldLabel(
            "", default_color=Common.color("modal_dialog_error")
        )
        self.add_field(self.error_label)
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


class ASGDescriber(Describer):
    prefix = "asg_browser"
    title = "Autoscaling Group"

    def __init__(self, *args, **kwargs):
        self.resource_key = "autoscaling"
        self.describe_method = "describe_auto_scaling_groups"
        self.describe_kwarg_name = "AutoScalingGroupNames"
        self.describe_kwarg_is_list = True
        self.object_path = ".AutoScalingGroups[0]"
        super().__init__(*args, **kwargs)
