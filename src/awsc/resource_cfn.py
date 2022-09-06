"""
Module for Cloudformation-related resources.
"""
import datetime

from .arn import ARN
from .base_control import (
    Describer,
    MultiLister,
    NoResults,
    ResourceLister,
    format_timedelta,
    tag_finder_generator,
)
from .common import Common
from .resource_common import multilister_with_compare_path


class CFNDescriber(Describer):
    """
    Describer control for Cloudformation Stack resources.
    """

    prefix = "cfn_browser"
    title = "CloudFormation Stack"

    def populate_entry(self, *args, **kwargs):
        super().populate_entry(*args, **kwargs)
        try:
            arn = ARN(self.entry_id)
            self.entry_id = arn.resource_id_first
        except ValueError:
            return

    def __init__(self, *args, **kwargs):
        self.resource_key = "cloudformation"
        self.describe_method = "describe_stacks"
        self.describe_kwarg_name = "StackName"
        self.object_path = ".Stacks[0]"
        super().__init__(*args, **kwargs)


# TODO: Refactor
class CFNRelated(MultiLister):
    """
    Related resource lister for Cloudformation Stack resources.
    """

    prefix = "cfn_related"
    title = "Resources in CloudFormation Stack"

    def title_info(self):
        return self.compare_value

    def __init__(self, *args, **kwargs):
        self.stack_res_list = {}
        kwargs["compare_key"] = "arn"
        self.resource_descriptors = [
            multilister_with_compare_path(
                "ec2", '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value'
            ),
            multilister_with_compare_path(
                "rds", '.TagList[] | select(.Key=="aws:cloudformation:stack-id").Value'
            ),
            {
                "resource_key": "autoscaling",
                "list_method": "describe_auto_scaling_groups",
                "list_kwargs": {},
                "item_path": ".AutoScalingGroups",
                "column_paths": {
                    "type": lambda x: "Autoscaling Group",
                    "id": self.empty,
                    "name": ".AutoScalingGroupName",
                },
                "hidden_columns": {},
                "compare_as_list": False,
                "compare_path": '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
            },
            {
                "resource_key": "elbv2",
                "list_method": "describe_load_balancers",
                "list_kwargs": {},
                "item_path": ".LoadBalancers",
                "column_paths": {
                    "type": lambda x: "Load Balancer",
                    "id": self.empty,
                    "name": ".LoadBalancerName",
                },
                "hidden_columns": {
                    "arn": ".LoadBalancerArn",
                },
                "compare_as_list": False,
                "compare_path": self.comparer_generator(
                    "AWS::ElasticLoadBalancingV2::LoadBalancer", ".LoadBalancerArn"
                ),
            },
            {
                "resource_key": "elbv2",
                "list_method": "describe_target_groups",
                "list_kwargs": {},
                "item_path": ".TargetGroups",
                "column_paths": {
                    "type": lambda x: "Target Group",
                    "id": self.resource_id_from_arn_generator(".TargetGroupArn"),
                    "name": ".TargetGroupName",
                },
                "hidden_columns": {
                    "arn": ".TargetGroupArn",
                },
                "compare_as_list": False,
                "compare_path": self.comparer_generator(
                    "AWS::ElasticLoadBalancingV2::TargetGroup", ".TargetGroupArn"
                ),
            },
            {
                "resource_key": "elbv2",
                "list_method": "describe_listeners",
                "list_kwargs": self.kwargs_from_physids_generator(
                    "ListenerArns", "AWS::ElasticLoadBalancingV2::Listener"
                ),
                "item_path": ".Listeners",
                "column_paths": {
                    "type": lambda x: "Listener",
                    "id": self.full_resource_id_from_arn_generator(".ListenerArn"),
                    "name": self.empty,
                },
                "hidden_columns": {
                    "arn": ".ListenerArn",
                },
                "compare_as_list": False,
                "compare_path": self.comparer_generator(
                    "AWS::ElasticLoadBalancingV2::Listener", ".ListenerArn"
                ),
            },
            {
                "resource_key": "ec2",
                "list_method": "describe_vpcs",
                "list_kwargs": {},
                "item_path": ".Vpcs",
                "column_paths": {
                    "type": lambda x: "VPC",
                    "id": ".VpcId",
                    "name": tag_finder_generator("Name"),
                },
                "hidden_columns": {},
                "compare_as_list": False,
                "compare_path": '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
            },
            {
                "resource_key": "ec2",
                "list_method": "describe_subnets",
                "list_kwargs": {},
                "item_path": ".Subnets",
                "column_paths": {
                    "type": lambda x: "VPC Subnet",
                    "id": ".SubnetId",
                    "name": tag_finder_generator("Name"),
                },
                "hidden_columns": {},
                "compare_as_list": False,
                "compare_path": '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
            },
            {
                "resource_key": "route53",
                "list_method": "list_hosted_zones",
                "list_kwargs": {},
                "item_path": ".HostedZones",
                "column_paths": {
                    "type": lambda x: "Route53 Zone",
                    "id": ".Id",
                    "name": ".Name",
                },
                "hidden_columns": {},
                "compare_as_list": False,
                "compare_path": self.comparer_generator(
                    "AWS::Route53::HostedZone", ".Id"
                ),
            },
            {
                "resource_key": "ec2",
                "list_method": "describe_vpcs",
                "list_kwargs": {},
                "item_path": ".Vpcs",
                "column_paths": {
                    "type": lambda x: "VPC",
                    "id": ".VpcId",
                    "name": tag_finder_generator("Name"),
                },
                "hidden_columns": {},
                "compare_as_list": False,
                "compare_path": '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
            },
            {
                "resource_key": "ec2",
                "list_method": "describe_subnets",
                "list_kwargs": {},
                "item_path": ".Subnets",
                "column_paths": {
                    "type": lambda x: "Subnet",
                    "id": ".SubnetId",
                    "name": tag_finder_generator("Name"),
                },
                "hidden_columns": {},
                "compare_as_list": False,
                "compare_path": '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
            },
            {
                "resource_key": "ec2",
                "list_method": "describe_route_tables",
                "list_kwargs": {},
                "item_path": ".RouteTables",
                "column_paths": {
                    "type": lambda x: "Route Table",
                    "id": ".RouteTableId",
                    "name": tag_finder_generator("Name"),
                },
                "hidden_columns": {},
                "compare_as_list": False,
                "compare_path": '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
            },
        ]
        super().__init__(*args, **kwargs)

    def full_resource_id_from_arn_generator(self, arn_path):
        """
        Column callback factory. Returns a function which retrieves the full resource ID from an ARN.

        Parameters
        ----------
        arn_path : str
            The jq path for the ARN.

        Returns
        -------
        callable(dict) -> str
            A function which retrieves the full resource ID from the ARN at arn_path.
        """

        def fn(raw_item):
            arn = ARN(Common.Session.jq(arn_path).input(raw_item).first())
            return arn.resource_id

        return fn

    def resource_id_from_arn_generator(self, arn_path):
        """
        Column callback factory. Returns a function which retrieves the first resource ID from an ARN.

        Parameters
        ----------
        arn_path : str
            The jq path for the ARN.

        Returns
        -------
        callable(dict) -> str
            A function which retrieves the first resource ID from the ARN at arn_path.
        """

        def fn(raw_item):
            arn = ARN(Common.Session.jq(arn_path).input(raw_item).first())
            return arn.resource_id_first

        return fn

    def comparer_generator(self, cfn_type, physical_id_path):
        """
        Comparer function generator. The comparer function generated by this generator determines whether a resource's physical ID is present
        in the list of physical resource IDs associated with the stack.

        If a MultiLister descriptor's compare_path is a function, the return value of that function is used for the comparison rather than the
        result of jq applied to the input. This enables us to use custom, more complex comparisons where required, while also retaining the
        ability to use very generic functions (such as one that simply returns the ID of the cloudformation stack a resource is associated
        with). For this reason, this comparer_generator can generate a compare_path function for us.

        Parameters
        ----------
        cfn_type : str
            Cloudformation type specification for the resources being compared by the comparer.
        physical_id_path : str
            The jq path where the resource's physical ID is available.

        Returns
        -------
        callable(dict) -> str
            A function which returns the stack ID of this stack if the resource is present in the stack, or None otherwise.
        """

        def fn(raw_item):
            phys_id = Common.Session.jq(physical_id_path).input(raw_item).first()
            if (
                cfn_type in self.stack_res_list
                and phys_id in self.stack_res_list[cfn_type]
            ):
                return self.compare_value
            return None

        return fn

    def kwargs_from_physids_generator(self, kwarg, cfn_type):
        """
        Kwargs callback factory. Returns a function which returns a list of physical IDs for stack resources with a certain Cloudformation
        type, as a dict, with a specified key.

        Parameters
        ----------
        kwarg : str
            The key for the resource ID list in the returned dict.
        cfn_type : str
            The Cloudformation type for which resource IDs will be listed.

        Returns
        -------
        callable() -> dict
            A function which returns a map mapping kwarg to the list of physical IDs of resources of type cfn_type.
        """

        def fn():
            if cfn_type in self.stack_res_list:
                return {kwarg: self.stack_res_list[cfn_type]}
            raise NoResults

        return fn

    def async_inner(self, *args, fn, clear=False, **kwargs):
        resource_list = {}
        self.stack_res_list = {}
        while True:
            rargs = {"StackName": self.orig_compare_value["name"]}
            if "NextToken" in resource_list and resource_list["NextToken"] is not None:
                rargs["NextToken"] = resource_list["NextToken"]
            resource_list = Common.Session.service_provider(
                "cloudformation"
            ).list_stack_resources(**rargs)
            for item in resource_list["StackResourceSummaries"]:
                if item["ResourceType"] not in self.stack_res_list:
                    self.stack_res_list[item["ResourceType"]] = []
                self.stack_res_list[item["ResourceType"]].append(
                    item["PhysicalResourceId"]
                )
            if "NextToken" not in resource_list or resource_list["NextToken"] is None:
                break
        return super().async_inner(*args, fn=fn, clear=clear, **kwargs)


def _cfn_determine_created(cfn):
    """
    Column callback for extracting when a stack was created.
    """
    return format_timedelta(
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.datetime.fromisoformat(cfn["CreationTime"])
    )


def _cfn_determine_updated(cfn):
    """
    Column callback for extracting when a stack was updated.
    """
    if "LastUpdatedTime" in cfn:
        return format_timedelta(
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.datetime.fromisoformat(cfn["LastUpdatedTime"])
        )
    return _cfn_determine_created(cfn)


class CFNResourceLister(ResourceLister):
    """
    Lister control for Cloudformation Stack resources.
    """

    prefix = "cfn_list"
    title = "CloudFormation Stacks"
    command_palette = ["cfn", "cloudformation"]

    resource_type = "stack"
    main_provider = "cloudformation"
    category = "Cloudformation"
    subcategory = "Stack"
    list_method = "describe_stacks"
    item_path = ".Stacks"
    columns = {
        "name": {"path": ".StackName", "size": 30, "weight": 0, "sort_weight": 0},
        "status": {"path": ".StackStatus", "size": 15, "weight": 1},
        "drift": {
            "path": ".DriftInformation.StackDriftStatus",
            "size": 15,
            "weight": 2,
        },
        "created": {"path": _cfn_determine_created, "size": 20, "weight": 3},
        "updated": {"path": _cfn_determine_updated, "size": 20, "weight": 4},
        "arn": {"path": ".StackId", "hidden": True},
    }
    describe_command = CFNDescriber.opener
    open_command = CFNRelated.opener
    open_selection_arg = "compare_value"


def _cfn_determine_parameter_value(param):
    if param["ParameterValue"] == "*" * len(param["ParameterValue"]):
        return "<hidden>"
    return param["ParameterValue"]


@ResourceLister.Autocommand("CFNResourceLister", "p", "Parameters", "stack")
class CFNParameters(ResourceLister):
    """
    Lister control for Cloudformation Stack parameters.
    """

    prefix = "cfn_list"
    title = "CloudFormation Stack Parameters"

    resource_type = "stack parameter"
    main_provider = "cloudformation"
    category = "Cloudformation"
    subcategory = "Stack Parameters"
    list_method = "describe_stacks"
    item_path = ".Stacks[0].Parameters"
    columns = {
        "name": {"path": ".ParameterKey", "size": 30, "weight": 0, "sort_weight": 0},
        "value": {"path": _cfn_determine_parameter_value, "size": 30, "weight": 1},
    }

    def title_info(self):
        return self.stack_name

    def __init__(self, *args, stack=None, **kwargs):
        self.stack_name = stack["name"]
        self.list_kwargs = {"StackName": stack["name"]}
        super().__init__(*args, **kwargs)


@ResourceLister.Autocommand("CFNResourceLister", "o", "Outputs", "stack")
class CFNOutputs(ResourceLister):
    """
    Lister control for Cloudformation Stack outputs.
    """

    prefix = "cfn_list"
    title = "CloudFormation Stack Outputs"

    resource_type = "stack output"
    main_provider = "cloudformation"
    category = "Cloudformation"
    subcategory = "Stack Outputs"
    list_method = "describe_stacks"
    item_path = ".Stacks[0].Outputs"
    columns = {
        "name": {"path": ".OutputKey", "size": 30, "weight": 0, "sort_weight": 0},
        "value": {"path": ".OutputValue", "size": 30, "weight": 1},
    }

    def title_info(self):
        return self.stack_name

    def __init__(self, *args, stack=None, **kwargs):
        self.stack_name = stack["name"]
        self.list_kwargs = {"StackName": stack["name"]}
        super().__init__(*args, **kwargs)
