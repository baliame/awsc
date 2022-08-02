from .base_control import (
    DeleteResourceDialog,
    Describer,
    ResourceLister,
    SingleRelationLister,
    SingleSelectorDialog,
)
from .common import Common
from .termui.alignment import CenterAnchor, Dimension
from .termui.dialog import DialogFieldCheckbox
from .termui.ui import ControlCodes


class EBApplicationResourceLister(ResourceLister):
    prefix = "eb_application_list"
    title = "Beanstalk Applications"
    command_palette = ["ebapplication", "ebapp", "elasticbeanstalkapplication"]

    def delete_application(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="application",
            resource_identifier=self.selection["name"],
            callback=self.do_delete,
            action_name="Delete",
            can_force=True,
        )

    def do_delete(self, force, **kwargs):
        if self.selection is None:
            return
        api_kwargs = {
            "ApplicationName": self.selection["name"],
            "TerminateEnvByForce": force,
        }
        Common.generic_api_call(
            "elasticbeanstalk",
            "delete_application",
            api_kwargs,
            "Delete application",
            "Elastic Beanstalk",
            subcategory="Application",
            success_template="Deleting application {0}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def __init__(self, *args, **kwargs):
        self.resource_key = "elasticbeanstalk"
        self.list_method = "describe_applications"
        self.item_path = ".Applications"
        self.column_paths = {
            "name": ".ApplicationName",
            "description": ".Description",
        }
        self.imported_column_sizes = {
            "name": 20,
            "description": 50,
        }
        self.hidden_columns = {
            "arn": ".ApplicationArn",
        }
        self.describe_command = EBApplicationDescriber.opener
        self.open_command = EBEnvironmentLister.opener
        self.open_selection_arg = "app"

        self.additional_commands = {
            "v": {
                "command": EBApplicationVersionResourceLister.opener,
                "selection_arg": "application",
                "tooltip": "View Versions",
            }
        }

        self.imported_column_order = ["name", "description"]
        self.sort_column = "name"
        self.primary_key = "name"
        super().__init__(*args, **kwargs)


class EBApplicationDescriber(Describer):
    prefix = "eb_application_browser"
    title = "Beanstalk Application"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_applications"
        self.describe_kwarg_name = "ApplicationNames"
        self.describe_kwarg_is_list = True
        self.object_path = ".Applications[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
        self.add_hotkey(ControlCodes.D, self.delete_application, "Delete application")


class EBApplicationVersionResourceLister(ResourceLister):
    prefix = "eb_application_version_list"
    title = "Beanstalk Application Versions"
    command_palette = [
        "ebapplicationversion",
        "ebappversion",
        "elasticbeanstalkapplicationversion",
    ]

    def delete_application_version(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="application version",
            resource_identifier=self.selection["name"],
            callback=self.do_delete,
            action_name="Delete",
            can_force=True,
        )

    def do_delete(self, **kwargs):
        if self.selection is None:
            return
        api_kwargs = {
            "ApplicationName": self.selection["application"],
            "VersionLabel": self.selection["version"],
        }
        Common.generic_api_call(
            "elasticbeanstalk",
            "delete_application_version",
            api_kwargs,
            "Delete appversion",
            "Elastic Beanstalk",
            subcategory="Application",
            success_template="Deleting application version {0}",
            resource=self.selection["version"],
        )
        self.refresh_data()

    def __init__(self, *args, application=None, **kwargs):
        self.application = application
        self.resource_key = "elasticbeanstalk"
        self.list_method = "describe_application_versions"
        if application is not None:
            self.list_kwargs = {"ApplicationName": self.application["name"]}
        self.item_path = ".ApplicationVersions"
        self.column_paths = {
            "application": ".ApplicationName",
            "version": ".VersionLabel",
            "status": ".Status",
            "description": ".Description",
        }
        self.imported_column_sizes = {
            "name": 20,
            "version": 20,
            "status": 10,
            "description": 50,
        }
        self.hidden_columns = {
            "name": ".VersionLabel",
        }
        self.describe_command = EBApplicationVersionDescriber.opener

        self.imported_column_order = ["name", "version", "status", "description"]
        self.sort_column = "name"
        self.primary_key = "name"
        super().__init__(*args, **kwargs)


class EBApplicationVersionDescriber(Describer):
    prefix = "eb_application_version_browser"
    title = "Beanstalk Application Version"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_application_versions"
        self.describe_kwarg_name = "VersionLabels"
        self.describe_kwarg_is_list = True
        self.describe_kwargs = {"ApplicationName": entry["application"]}
        self.object_path = ".Applications[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
        self.add_hotkey(
            ControlCodes.D, self.delete_application_version, "Delete app version"
        )


class EBEnvironmentLister(ResourceLister):
    prefix = "eb_environment_list"
    title = "Beanstalk Environments"
    command_palette = ["ebenvironment", "ebenv", "elasticbeanstalkenvironment"]

    def delete_environment(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="environment",
            resource_identifier=self.selection["name"],
            callback=self.do_delete,
            action_name="Delete",
            can_force=True,
            extra_fields={
                "terminate_resources_field": DialogFieldCheckbox(
                    "Terminate resources",
                    checked=False,
                    color=Common.color("modal_dialog_textfield_label"),
                    selected_color=Common.color("modal_dialog_textfield_selected"),
                )
            },
        )

    def do_delete(self, force, terminate_resources_field, **kwargs):
        if self.selection is None:
            return
        api_kwargs = {
            "EnvironmentName": self.selection["name"],
            "ForceTerminate": force,
            "TerminateResources": terminate_resources_field.checked,
        }
        Common.generic_api_call(
            "elasticbeanstalk",
            "terminate_environment",
            api_kwargs,
            "Terminate environment",
            "Elastic Beanstalk",
            subcategory="Environment",
            success_template="Terminating environment {0}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def delete_environment_config(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="environment configuration",
            resource_identifier=self.selection["name"],
            callback=self.do_delete_config,
            action_name="Delete",
        )

    def do_delete_config(self, force, terminate_resources_field, **kwargs):
        if self.selection is None:
            return
        api_kwargs = {
            "EnvironmentName": self.selection["name"],
            "ApplicationName": self.selection["application"],
        }
        Common.generic_api_call(
            "elasticbeanstalk",
            "delete_environment_configuration",
            api_kwargs,
            "Delete envconfig",
            "Elastic Beanstalk",
            subcategory="Environment",
            success_template="Deleting environment {0} configuration",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def rebuild_environment(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="environment",
            resource_identifier=self.selection["name"],
            callback=self.do_rebuild,
            action_name="Rebuild",
        )

    def do_rebuild(self, **kwargs):
        if self.selection is None:
            return
        api_kwargs = {
            "EnvironmentName": self.selection["name"],
        }
        Common.generic_api_call(
            "elasticbeanstalk",
            "rebuild_environment",
            api_kwargs,
            "Rebuild environment",
            "Elastic Beanstalk",
            subcategory="Environment",
            success_template="Rebuilding environment {0}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def swap_cnames(self, _):
        if self.selection is None:
            return
        SingleSelectorDialog(
            self.parent,
            "Swap CNames of environment '{0}' with other environment".format(
                self.selection["name"]
            ),
            "environment",
            "swap",
            EBEnvironmentLister,
            self.do_swap,
            caller=self,
        )

    def do_swap(self, other_env):
        if self.selection is None:
            return
        if other_env == self.selection["name"]:
            Common.Session.error(
                "Source and destination environments are the same.",
                "Swap Cnames",
                "Elastic Beanstalk",
                resource=self.selection["name"],
            )
            return
        api_kwargs = {
            "SourceEnvironmentName": self.selection["name"],
            "DestinationEnvironmentName": other_env,
        }
        Common.generic_api_call(
            "elasticbeanstalk",
            "swap_environment_cnames",
            api_kwargs,
            "Swap Cnames",
            "Elastic Beanstalk",
            subcategory="Environment",
            success_template="Swapping cnames for environments {0}",
            resource="{0}, {1}".format(self.selection["name"], other_env),
        )
        self.refresh_data()

    def __init__(self, *args, app=None, **kwargs):
        self.resource_key = "elasticbeanstalk"
        self.list_method = "describe_environments"
        self.item_path = ".Environments"
        self.app = app
        if app is not None:
            self.list_kwargs = {"ApplicationName": self.app}
        self.column_paths = {
            "name": ".EnvironmentName",
            "id": ".EnvironmentId",
            "application": ".ApplicationName",
            "status": ".Status",
            "health": ".Health",
            "tier": ".Tier.Name",
        }
        self.imported_column_sizes = {
            "name": 20,
            "id": 20,
            "application": 20,
            "status": 15,
            "health": 7,
            "tier": 10,
        }
        self.hidden_columns = {
            "arn": ".EnvironmentArn",
        }
        self.describe_command = EBEnvironmentDescriber.opener
        # self.open_command = EBEnvironmentLister.opener
        # self.open_selection_arg = 'lb'

        self.imported_column_order = [
            "name",
            "id",
            "tier",
            "status",
            "health",
            "application",
        ]
        self.sort_column = "name"
        self.primary_key = "name"
        self.additional_commands = {
            "v": {
                "command": EBEnvironmentResourceLister.opener,
                "selection_arg": "environment",
                "tooltip": "View env resources",
            },
            "i": {
                "command": EBInstanceHealthLister.opener,
                "selection_arg": "environment",
                "tooltip": "View instance healths",
            },
            "h": {
                "command": EBEnvironmentHealthDescriber.opener,
                "selection_arg": "entry",
                "tooltip": "View env health",
            },
        }
        super().__init__(*args, **kwargs)
        if self.selector_cb is None:
            self.add_hotkey(
                ControlCodes.B, self.rebuild_environment, "Rebuild environment"
            )
            self.add_hotkey(ControlCodes.S, self.swap_cnames, "Swap CNames")
            self.add_hotkey(
                ControlCodes.D, self.delete_environment, "Terminate environment"
            )
            self.add_hotkey(
                ControlCodes.E, self.delete_environment, "Delete env config"
            )

    def title_info(self):
        return self.app


class EBEnvironmentDescriber(Describer):
    prefix = "eb_environment_browser"
    title = "Beanstalk Environment"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_environments"
        self.describe_kwarg_name = "EnvironmentNames"
        self.describe_kwarg_is_list = True
        self.object_path = ".Environments[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class EBEnvironmentHealthDescriber(Describer):
    prefix = "eb_environment_health_browser"
    title = "Beanstalk Environment Health"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_environment_health"
        self.describe_kwarg_name = "EnvironmentName"
        self.describe_kwarg_is_list = True
        self.object_path = "."
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class EBEnvironmentResourceLister(SingleRelationLister):
    prefix = "eb_environment_resources"
    title = "Beanstalk Environment resources"

    def title_info(self):
        return self.environment["name"]

    def __init__(self, *args, environment=None, **kwargs):
        from .resource_asg import ASGDescriber
        from .resource_ec2 import EC2Describer
        from .resource_lb import LBDescriber
        from .resource_lc import LCDescriber
        from .resource_sqs import SQSDescriber

        self.resource_key = "elasticbeanstalk"
        self.environment = environment
        self.describe_method = "describe_environment_resources"
        self.describe_kwargs = {"EnvironmentName": self.environment["name"]}
        self.object_path = ".EnvironmentResources"
        self.resource_descriptors = [
            {
                "base_path": "[.AutoscalingGroups[].Name]",
                "type": "Auto Scaling Group",
                "describer": ASGDescriber.opener,
            },
            {
                "base_path": "[.Instances[].Id]",
                "type": "EC2 Instance",
                "describer": EC2Describer.opener,
            },
            {
                "base_path": "[.LaunchConfigurations[].Name]",
                "type": "Launch Configuration",
                "describer": LCDescriber.opener,
            },
            {
                "base_path": "[.LaunchTemplates[].Name]",
                "type": "Launch Templates",
            },
            {
                "base_path": "[.LoadBalancers[].Name]",
                "type": "Load Balancer",
                "describer": LBDescriber.opener,
            },
            {
                "base_path": "[.Triggers[].Name]",
                "type": "Trigger",
            },
            {
                "base_path": "[.Queues[].URL]",
                "type": "SQS Queue",
                "describer": SQSDescriber.opener,
            },
        ]
        super().__init__(*args, **kwargs)


class EBPlatformBranchLister(ResourceLister):
    prefix = "eb_platform_version_list"
    title = "Beanstalk Platform Branches"
    command_palette = [
        "platformbranch",
        "ebplatformbranch",
        "elasticbeanstalkplatformbranch",
    ]

    def __init__(self, *args, **kwargs):
        self.resource_key = "elasticbeanstalk"
        self.list_method = "list_platform_branches"
        self.item_path = ".PlatformBranchSummaryList"
        self.column_paths = {
            "platform": ".PlatformName",
            "branch": ".BranchName",
            "lifecycle": ".LifecycleState",
            "order": ".BranchOrder",
        }
        self.imported_column_sizes = {
            "platform": 20,
            "branch": 20,
            "lifecycle": 20,
            "order": 10,
        }
        self.hidden_columns = {
            "name": ".BranchName",
        }
        self.describe_command = EBPlatformVersionDescriber.opener

        self.imported_column_order = [
            "branch",
            "platform",
            "lifecycle",
            "order",
        ]
        self.sort_column = "branch"
        self.primary_key = "name"
        self.additional_commands = {
            "v": {
                "command": EBPlatformVersionLister.opener,
                "selection_arg": "branch",
                "tooltip": "View Versions",
            }
        }
        super().__init__(*args, **kwargs)


class EBPlatformBranchDescriber(Describer):
    prefix = "eb_platform_branch_browser"
    title = "Beanstalk Platform Branch"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="arn", **kwargs
    ):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_platform_version"
        self.describe_kwarg_name = "PlatformArn"
        self.object_path = ".PlatformDescription"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class EBPlatformVersionLister(ResourceLister):
    prefix = "eb_platform_version_list"
    title = "Beanstalk Platform Versions"
    command_palette = [
        "platformversion",
        "ebplatformversion",
        "elasticbeanstalkplatformversion",
    ]

    def title_info(self):
        if self.branch is not None:
            return "Branch: {0}".format(self.branch["name"])
        return None

    def __init__(self, *args, branch=None, **kwargs):
        self.branch = branch
        self.resource_key = "elasticbeanstalk"
        self.list_method = "list_platform_versions"
        if self.branch is not None:
            self.list_kwargs = {
                "Filters": [
                    {
                        "Type": "PlatformBranchName",
                        "Operator": "=",
                        "Values": [self.branch["name"]],
                    }
                ]
            }
        self.item_path = ".PlatformSummaryList"
        self.column_paths = {
            "owner": ".PlatformOwner",
            "os": ".OperatingSystemName",
            "os version": ".OperatingSystemVersion",
            "status": ".PlatformStatus",
            "category": ".PlatformCategory",
            "version": ".PlatformVersion",
            "lifecycle": ".PlatformLifecycleState",
        }
        self.imported_column_sizes = {
            "owner": 10,
            "os": 20,
            "os version": 10,
            "status": 10,
            "category": 10,
            "version": 10,
            "lifecycle": 10,
        }
        self.hidden_columns = {
            "name": ".PlatformArn",
            "arn": ".PlatformArn",
        }
        self.describe_command = EBPlatformVersionDescriber.opener

        self.imported_column_order = [
            "owner",
            "os",
            "os version",
            "category",
            "version",
            "status",
            "lifecycle",
        ]
        self.sort_column = "name"
        self.primary_key = "name"
        super().__init__(*args, **kwargs)


class EBPlatformVersionDescriber(Describer):
    prefix = "eb_platform_version_browser"
    title = "Beanstalk Platform Version"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="arn", **kwargs
    ):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_platform_version"
        self.describe_kwarg_name = "PlatformArn"
        self.object_path = ".PlatformDescription"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class EBInstanceHealthLister(ResourceLister):
    prefix = "eb_instance_health_list"
    title = "Beanstalk Instance Health"

    def __init__(self, *args, environment=None, **kwargs):
        from .resource_ec2 import EC2Describer

        self.environment = environment
        self.resource_key = "elasticbeanstalk"
        self.list_method = "describe_instances_health"
        self.list_kwargs = {"EnvironmentName": environment["name"]}
        self.item_path = ".InstanceHealthList"
        self.column_paths = {
            "instance id": ".InstanceId",
            "status": ".HealthStatus",
            "color": ".Color",
            "az": ".AvailabilityZone",
            "type": ".InstanceType",
        }
        self.imported_column_sizes = {
            "instance id": 20,
            "az": 20,
            "type": 20,
            "color": 20,
            "status": 20,
        }
        self.hidden_columns = {
            "name": ".InstanceId",
        }
        self.describe_command = EBInstanceHealthDescriber.opener
        self.additional_commands = {
            "v": {
                "command": EC2Describer.opener,
                "selection_arg": "entry",
                "tooltip": "Describe EC2 Instance",
            }
        }

        self.imported_column_order = [
            "instance id",
            "az",
            "type",
            "color",
            "status",
        ]
        self.sort_column = "name"
        self.primary_key = "name"
        super().__init__(*args, **kwargs)


class EBInstanceHealthDescriber(Describer):
    prefix = "eb_instance_health_browser"
    title = "Beanstalk Instance"

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        entry,
        *args,
        entry_key="instance id",
        caller=None,
        **kwargs
    ):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_instances_health"
        self.describe_kwargs = {"EnvironmentName": caller.environment["name"]}
        self.object_path = ".InstanceList[] | select(.InstanceId=={0})".format(
            entry[entry_key]
        )
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
