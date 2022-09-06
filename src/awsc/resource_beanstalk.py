"""
Module for Elastic Beanstalk-related resources.
"""

from .base_control import (
    Describer,
    FieldValue,
    ForceFlag,
    ResourceLister,
    ResourceRefByClass,
    ResourceRefByCommand,
    SelectionAttribute,
    SingleRelationLister,
    SingleSelectorDialog,
    TemplateDict,
)
from .common import Common
from .termui.dialog import DialogFieldCheckbox
from .termui.ui import ControlCodes


class EBApplicationDescriber(Describer):
    """
    Describer control for Beanstalk Application resources.
    """

    prefix = "eb_application_browser"
    title = "Beanstalk Application"

    def __init__(self, *args, **kwargs):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_applications"
        self.describe_kwarg_name = "ApplicationNames"
        self.describe_kwarg_is_list = True
        self.object_path = ".Applications[0]"
        super().__init__(*args, **kwargs)


class EBApplicationResourceLister(ResourceLister):
    """
    Lister control for Beanstalk Application resources.
    """

    prefix = "eb_application_list"
    title = "Beanstalk Applications"
    command_palette = ["ebapplication", "ebapp", "elasticbeanstalkapplication"]

    resource_type = "application"
    main_provider = "elasticbeanstalk"
    category = "Elastic Beanstalk"
    subcategory = "Application"
    list_method = "describe_applications"
    item_path = ".Applications"
    columns = {
        "name": {"path": ".ApplicationName", "size": 20, "weight": 0, "sort_weight": 0},
        "description": {"path": ".Description", "size": 50, "weight": 1},
        "arn": {"path": ".ApplicationArn", "hidden": True},
    }
    describe_command = EBApplicationDescriber.opener
    open_command = ResourceRefByCommand("elasticbeanstalkenvironment")
    open_selection_arg = "app"

    @ResourceLister.Autohotkey(ControlCodes.D, "Delete application", True)
    def delete_application(self, *args, **kwargs):
        """
        Hotkey definition for deleting an application.
        """
        self.confirm_template(
            "delete_application",
            TemplateDict(
                {
                    "ApplicationName": SelectionAttribute("name"),
                    "TerminateEnvByForce": ForceFlag(),
                }
            ),
            can_force=True,
        )(self.selection)


class EBApplicationVersionDescriber(Describer):
    """
    Describer control for Beanstalk Application Version resources.
    """

    prefix = "eb_application_version_browser"
    title = "Beanstalk Application Version"

    def __init__(self, *args, entry, **kwargs):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_application_versions"
        self.describe_kwarg_name = "VersionLabels"
        self.describe_kwarg_is_list = True
        self.describe_kwargs = {"ApplicationName": entry["application"]}
        self.object_path = ".Applications[0]"
        super().__init__(*args, entry=entry, **kwargs)


@ResourceLister.Autocommand("EBApplicationLister", "v", "View Versions", "application")
class EBApplicationVersionResourceLister(ResourceLister):
    """
    Lister control for Beanstalk Application Version resources.
    """

    prefix = "eb_application_version_list"
    title = "Beanstalk Application Versions"
    command_palette = [
        "ebapplicationversion",
        "ebappversion",
        "elasticbeanstalkapplicationversion",
    ]

    resource_type = "appversion"
    main_provider = "elasticbeanstalk"
    category = "Elastic Beanstalk"
    subcategory = "Appversion"
    list_method = "describe_application_versions"
    item_path = ".ApplicationVersions"
    columns = {
        "application": {
            "path": ".ApplicationName",
            "size": 20,
            "weight": 0,
            "sort_weight": 0,
        },
        "version": {"path": ".VersionLabel", "size": 20, "weight": 1, "sort_weight": 1},
        "status": {"path": ".Status", "size": 20, "weight": 2},
        "description": {"path": ".Description", "size": 50, "weight": 3},
        "name": {"path": ".VersionLabel", "hidden": True},
    }
    describe_command = EBApplicationVersionDescriber.opener

    def __init__(self, *args, application=None, **kwargs):
        self.application = application
        if application is not None:
            self.list_kwargs = {"ApplicationName": self.application["name"]}
        super().__init__(*args, **kwargs)
        self.confirm_template(
            "delete_application_version",
            TemplateDict(
                {
                    "ApplicationName": SelectionAttribute("name"),
                    "VersionLabel": SelectionAttribute("version"),
                }
            ),
            can_force=True,
            hotkey=ControlCodes.D,
            hotkey_tooltip="Delete appversion",
        )


class EBEnvironmentDescriber(Describer):
    """
    Describer control for Beanstalk Environment resources.
    """

    prefix = "eb_environment_browser"
    title = "Beanstalk Environment"

    def __init__(self, *args, **kwargs):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_environments"
        self.describe_kwarg_name = "EnvironmentNames"
        self.describe_kwarg_is_list = True
        self.object_path = ".Environments[0]"
        super().__init__(*args, **kwargs)


@ResourceLister.Autocommand("EBEnvironmentLister", "h", "Environment health", "entry")
class EBEnvironmentHealthDescriber(Describer):
    """
    Describer control for Beanstalk Environment resource health state.
    """

    prefix = "eb_environment_health_browser"
    title = "Beanstalk Environment Health"

    def __init__(self, *args, **kwargs):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_environment_health"
        self.describe_kwarg_name = "EnvironmentName"
        self.describe_kwarg_is_list = True
        self.object_path = "."
        super().__init__(*args, **kwargs)


class EBEnvironmentLister(ResourceLister):
    """
    Lister control for Beanstalk Environment resources.
    """

    prefix = "eb_environment_list"
    title = "Beanstalk Environments"
    command_palette = ["ebenvironment", "ebenv", "elasticbeanstalkenvironment"]

    resource_type = "environment"
    main_provider = "elasticbeanstalk"
    category = "Elastic Beanstalk"
    subcategory = "Environment"
    list_method = "describe_environments"
    item_path = ".Environments"
    columns = {
        "name": {"path": ".EnvironmentName", "size": 20, "weight": 0, "sort_weight": 1},
        "id": {"path": ".EnvironmentId", "size": 20, "weight": 1},
        "application": {
            "path": ".ApplicationName",
            "size": 20,
            "weight": 2,
            "sort_weight": 0,
        },
        "status": {"path": ".Status", "size": 15, "weight": 3, "sort_weight": 0},
        "health": {"path": ".Health", "size": 7, "weight": 4, "sort_weight": 0},
        "tier": {"path": ".Tier.Name", "size": 10, "weight": 5, "sort_weight": 0},
        "arn": {"path": ".EnvironmentArn", "hidden": True},
    }
    describe_command = EBEnvironmentDescriber.opener

    @ResourceLister.Autohotkey(ControlCodes.D, "Terminate environment", True, True)
    def delete_environment(self, _):
        """
        Hotkey callback for deleting an environment.
        """
        self.confirm_template(
            "terminate_environment",
            TemplateDict(
                {
                    "EnvironmentName": SelectionAttribute("name"),
                    "ForceTerminate": ForceFlag(),
                    "TerminateResources": FieldValue("terminate_resources_field"),
                }
            ),
            can_force=True,
            extra_fields={
                "terminate_resources_field": DialogFieldCheckbox(
                    "Terminate resources",
                    checked=False,
                    color=Common.color("modal_dialog_textfield_label"),
                    selected_color=Common.color("modal_dialog_textfield_selected"),
                )
            },
        )(self.selection)

    @ResourceLister.Autohotkey(ControlCodes.E, "Delete envconfig", True, True)
    def delete_environment_config(self, _):
        """
        Hotkey callback for deleting an environment configuration.
        """
        self.confirm_template(
            "delete_environment_config",
            TemplateDict(
                {
                    "EnvironmentName": SelectionAttribute("name"),
                    "ApplicationName": SelectionAttribute("application"),
                }
            ),
            resource_type="environment configuration",
        )(self.selection)

    @ResourceLister.Autohotkey(ControlCodes.B, "Rebuild environment", True, True)
    def rebuild_environment(self, _):
        """
        Hotkey callback for rebuilding an environment configuration.
        """
        self.confirm_template(
            "rebuild_environment",
            TemplateDict(
                {
                    "EnvironmentName": SelectionAttribute("name"),
                }
            ),
            action_name="Rebuild",
        )(self.selection)

    @ResourceLister.Autohotkey(ControlCodes.S, "Swap CNames", True, True)
    def swap_cnames(self, _):
        """
        Hotkey callback for swapping environment cnames.
        """
        SingleSelectorDialog.opener(
            f"Swap CNames of environment '{self.selection['name']}' with other environment",
            "environment",
            "swap",
            EBEnvironmentLister,
            self.do_swap,
            caller=self,
        )

    def do_swap(self, other_env):
        """
        Action callback for environment cname swap dialog.
        """
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
            resource=f"{self.selection['name']}, {other_env}",
        )
        self.refresh_data()

    def __init__(self, *args, app=None, **kwargs):
        self.app = app["name"]
        if app is not None:
            self.list_kwargs["ApplicationName"] = self.app
        super().__init__(*args, **kwargs)

    def title_info(self):
        return self.app


@ResourceLister.Autocommand("EBEnvironmentLister", "v", "View resources", "selection")
class EBEnvironmentResourceLister(SingleRelationLister):
    """
    Lister control for Beanstalk Environment related resources.
    """

    prefix = "eb_environment_resources"
    title = "Beanstalk Environment resources"

    resource_type = "beanstalk environment"
    main_provider = "elasticbeanstalk"
    category = "Elastic Beanstalk"
    subcategory = "Environment"
    describe_method = "describe_environment_resources"
    describe_kwargs = TemplateDict({"EnvironmentName": SelectionAttribute("name")})
    object_path = ".EnvironmentResources"
    resource_descriptors = [
        {
            "base_path": "[.AutoscalingGroups[].Name]",
            "type": "Auto Scaling Group",
            "describer": ResourceRefByClass("ASGDescriber"),
        },
        {
            "base_path": "[.Instances[].Id]",
            "type": "EC2 Instance",
            "describer": ResourceRefByClass("EC2Describer"),
        },
        {
            "base_path": "[.LaunchConfigurations[].Name]",
            "type": "Launch Configuration",
            "describer": ResourceRefByClass("LCDescriber"),
        },
        {
            "base_path": "[.LaunchTemplates[].Name]",
            "type": "Launch Templates",
        },
        {
            "base_path": "[.LoadBalancers[].Name]",
            "type": "Load Balancer",
            "describer": ResourceRefByClass("LBDescriber"),
        },
        {
            "base_path": "[.Triggers[].Name]",
            "type": "Trigger",
        },
        {
            "base_path": "[.Queues[].URL]",
            "type": "SQS Queue",
            "describer": ResourceRefByClass("SQSDescriber"),
        },
    ]

    def title_info(self):
        return f"Environment: {self.parent_selection['name']}"


class EBPlatformBranchLister(ResourceLister):
    """
    Lister control for Beanstalk Platform Branch resources.
    """

    prefix = "eb_platform_version_list"
    title = "Beanstalk Platform Branches"
    command_palette = [
        "platformbranch",
        "ebplatformbranch",
        "elasticbeanstalkplatformbranch",
    ]

    resource_type = "platform branch"
    main_provider = "elasticbeanstalk"
    category = "Elastic Beanstalk"
    subcategory = "Platform Branch"
    list_method = "list_platform_branches"
    item_path = ".PlatformBranchSummaryList"
    columns = {
        "platform": {
            "path": ".PlatformName",
            "size": 20,
            "weight": 0,
            "sort_weight": 0,
        },
        "branch": {"path": ".BranchName", "size": 20, "weight": 1, "sort_weight": 1},
        "lifecycle": {
            "path": ".LifecycleState",
            "size": 20,
            "weight": 2,
        },
        "order": {"path": ".BranchOrder", "size": 10, "weight": 3},
        "name": {"path": ".BranchName", "hidden": True},
    }
    describe_command = ResourceRefByCommand("elasticbeanstalkplatformversion")
    describe_selection_arg = "branch"


class EBPlatformVersionDescriber(Describer):
    """
    Describer control for Beanstalk Platform Versions.
    """

    prefix = "eb_platform_version_browser"
    title = "Beanstalk Platform Version"

    def __init__(self, *args, entry_key="arn", **kwargs):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_platform_version"
        self.describe_kwarg_name = "PlatformArn"
        self.object_path = ".PlatformDescription"
        super().__init__(*args, entry_key=entry_key, **kwargs)


class EBPlatformVersionLister(ResourceLister):
    """
    Lister control for Beanstalk Platform Versions.
    """

    prefix = "eb_platform_version_list"
    title = "Beanstalk Platform Versions"
    command_palette = [
        "platformversion",
        "ebplatformversion",
        "elasticbeanstalkplatformversion",
    ]

    resource_type = "platform version"
    main_provider = "elasticbeanstalk"
    category = "Elastic Beanstalk"
    subcategory = "Platform Version"
    list_method = "list_platform_versions"
    item_path = ".PlatformSummaryList"
    columns = {
        "owner": {
            "path": ".PlatformOwner",
            "size": 10,
            "weight": 0,
            "sort_weight": 2,
        },
        "os": {
            "path": ".OperatingSystemName",
            "size": 20,
            "weight": 1,
            "sort_weight": 0,
        },
        "os version": {
            "path": ".OperatingSystemVersion",
            "size": 10,
            "weight": 2,
            "sort_weight": 1,
        },
        "status": {"path": ".PlatformStatus", "size": 10, "weight": 3},
        "category": {"path": ".PlatformCategory", "size": 10, "weight": 4},
        "version": {"path": ".PlatformVersion", "size": 10, "weight": 5},
        "lifecycle": {"path": ".PlatformLifecycleState", "size": 10, "weight": 6},
        "name": {"path": ".PlatformArn", "hidden": True},
        "arn": {"path": ".PlatformArn", "hidden": True},
    }
    describe_command = EBPlatformVersionDescriber.opener

    def title_info(self):
        return f"Branch: {self.branch['name']}" if self.branch is not None else None

    def __init__(self, *args, branch=None, **kwargs):
        self.branch = branch
        if branch is not None:
            self.list_kwargs = {
                "Filters": [
                    {
                        "Type": "PlatformBranchName",
                        "Operator": "=",
                        "Values": [branch["name"]],
                    }
                ]
            }
        super().__init__(*args, **kwargs)


class EBInstanceHealthDescriber(Describer):
    """
    Describer control for instance health.
    """

    prefix = "eb_instance_health_browser"
    title = "Beanstalk Instance"

    def __init__(
        self,
        *args,
        entry,
        entry_key="instance id",
        caller=None,
        **kwargs,
    ):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_instances_health"
        self.describe_kwargs = {"EnvironmentName": caller.environment["name"]}
        self.object_path = f".InstanceList[] | select(.InstanceId=={entry[entry_key]})"
        super().__init__(
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs,
        )


@ResourceLister.Autocommand(
    "EBEnvironmentLister", "i", "View instance healths", "environment"
)
class EBInstanceHealthLister(ResourceLister):
    """
    Lister control for instance healths in Beanstalk Environments.
    """

    prefix = "eb_instance_health_list"
    title = "Beanstalk Instance Health"

    resource_type = "instance health"
    main_provider = "elasticbeanstalk"
    category = "Elastic Beanstalk"
    subcategory = "Instance Health"
    list_method = "describe_instances_health"
    item_path = ".InstanceHealthList"
    columns = {
        "instance id": {
            "path": ".InstanceId",
            "size": 20,
            "weight": 0,
            "sort_weight": 0,
        },
        "az": {"path": ".AvailabilityZone", "size": 20, "weight": 1},
        "type": {"path": ".InstanceType", "size": 20, "weight": 2},
        "status": {"path": ".HealthStatus", "size": 20, "weight": 3},
        "color": {"path": ".Color", "size": 20, "weight": 4},
        "name": {"path": ".InstanceId", "hidden": True},
    }
    describe_command = EBInstanceHealthDescriber.opener

    def __init__(self, *args, environment=None, **kwargs):
        self.environment = environment
        self.list_kwargs = {"EnvironmentName": environment["name"]}
        super().__init__(*args, **kwargs)
