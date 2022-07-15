import datetime

from .arn import ARN
from .base_control import (
    Describer,
    MultiLister,
    NoResults,
    ResourceLister,
    format_timedelta,
)
from .common import Common


class CFNResourceLister(ResourceLister):
    prefix = "cfn_list"
    title = "CloudFormation Stacks"
    command_palette = ["cfn", "cloudformation"]

    def __init__(self, *args, **kwargs):
        self.resource_key = "cloudformation"
        self.list_method = "describe_stacks"
        self.item_path = ".Stacks"
        self.column_paths = {
            "name": ".StackName",
            "status": ".StackStatus",
            "drift": ".DriftInformation.StackDriftStatus",
            "created": self.determine_created,
            "updated": self.determine_updated,
        }
        self.hidden_columns = {
            "arn": ".StackId",
        }
        self.imported_column_sizes = {
            "name": 30,
            "status": 15,
            "drift": 15,
            "created": 20,
            "updated": 20,
        }
        self.describe_command = CFNDescriber.opener
        self.open_command = CFNRelated.opener
        self.open_selection_arg = "compare_value"

        self.imported_column_order = ["name", "status", "drift", "created", "updated"]
        self.sort_column = "name"
        self.primary_key = "name"
        super().__init__(*args, **kwargs)
        self.add_hotkey("p", self.parameters, "Parameters")
        self.add_hotkey("o", self.outputs, "Outputs")

    def parameters(self, _):
        if self.selection is not None:
            Common.Session.push_frame(CFNParameters.opener(stack=self.selection))

    def outputs(self, _):
        if self.selection is not None:
            Common.Session.push_frame(CFNOutputs.opener(stack=self.selection))

    def determine_created(self, cfn):
        return format_timedelta(
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.datetime.fromisoformat(cfn["CreationTime"])
        )

    def determine_updated(self, cfn):
        if "LastUpdatedTime" in cfn:
            return format_timedelta(
                datetime.datetime.now(datetime.timezone.utc)
                - datetime.datetime.fromisoformat(cfn["LastUpdatedTime"])
            )
        return self.determine_created(cfn)


class CFNDescriber(Describer):
    prefix = "cfn_browser"
    title = "CloudFormation Stack"

    def populate_entry(self, *args, **kwargs):
        super().populate_entry(*args, **kwargs)
        try:
            arn = ARN(self.entry_id)
            self.entry_id = arn.resource_id_first
        except ValueError:
            return

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "cloudformation"
        self.describe_method = "describe_stacks"
        self.describe_kwarg_name = "StackName"
        self.object_path = ".Stacks[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class CFNRelated(MultiLister):
    prefix = "cfn_related"
    title = "Resources in CloudFormation Stack"

    def title_info(self):
        return self.compare_value

    def __init__(self, *args, **kwargs):
        kwargs["compare_key"] = "arn"
        self.resource_descriptors = [
            {
                "resource_key": "ec2",
                "list_method": "describe_instances",
                "list_kwargs": {},
                "item_path": "[.Reservations[].Instances[]]",
                "column_paths": {
                    "type": lambda x: "EC2 Instance",
                    "id": ".InstanceId",
                    "name": self.tag_finder_generator("Name"),
                },
                "hidden_columns": {},
                "compare_as_list": False,
                "compare_path": '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
            },
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
                "resource_key": "rds",
                "list_method": "describe_db_instances",
                "list_kwargs": {},
                "item_path": ".DBInstances",
                "column_paths": {
                    "type": lambda x: "RDS Instance",
                    "id": ".DBInstanceIdentifier",
                    "name": ".Endpoint.Address",
                },
                "hidden_columns": {},
                "compare_as_list": False,
                "compare_path": '.TagList[] | select(.Key=="aws:cloudformation:stack-id").Value',
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
                    "name": self.tag_finder_generator("Name"),
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
                    "name": self.tag_finder_generator("Name"),
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
                    "name": self.tag_finder_generator("Name"),
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
                    "name": self.tag_finder_generator("Name"),
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
                    "name": self.tag_finder_generator("Name"),
                },
                "hidden_columns": {},
                "compare_as_list": False,
                "compare_path": '.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value',
            },
        ]
        super().__init__(*args, **kwargs)

    def full_resource_id_from_arn_generator(self, arn_path):
        def fn(raw_item):
            arn = ARN(Common.Session.jq(arn_path).input(raw_item).first())
            return arn.resource_id

        return fn

    def resource_id_from_arn_generator(self, arn_path):
        def fn(raw_item):
            arn = ARN(Common.Session.jq(arn_path).input(raw_item).first())
            return arn.resource_id_first

        return fn

    def comparer_generator(self, cfn_type, physical_id_path):
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
        def fn():
            if cfn_type in self.stack_res_list:
                return {kwarg: self.stack_res_list[cfn_type]}
            raise NoResults

        return fn

    def async_inner(self, *args, fn, clear=False, **kwargs):
        stop = False
        rl = None
        self.stack_res_list = {}
        while not stop:
            rargs = {"StackName": self.orig_compare_value["name"]}
            if rl is not None and "NextToken" in rl and rl["NextToken"] is not None:
                rargs["NextToken"] = rl["NextToken"]
            rl = Common.Session.service_provider("cloudformation").list_stack_resources(
                **rargs
            )
            if "NextToken" not in rl or rl["NextToken"] is None:
                stop = True
            for item in rl["StackResourceSummaries"]:
                if item["ResourceType"] not in self.stack_res_list:
                    self.stack_res_list[item["ResourceType"]] = []
                self.stack_res_list[item["ResourceType"]].append(
                    item["PhysicalResourceId"]
                )
        return super().async_inner(*args, fn=fn, clear=clear, **kwargs)


class CFNParameters(ResourceLister):
    prefix = "cfn_list"
    title = "CloudFormation Stack Parameters"

    def title_info(self):
        return self.stack_name

    def __init__(self, *args, stack=None, **kwargs):
        self.resource_key = "cloudformation"
        self.list_method = "describe_stacks"
        self.item_path = ".Stacks[0].Parameters"
        self.column_paths = {
            "name": ".ParameterKey",
            "value": self.determine_value,
        }
        self.list_kwargs = {"StackName": stack["name"]}
        self.imported_column_sizes = {
            "name": 30,
            "value": 30,
        }
        self.imported_column_order = ["name", "value"]

        self.sort_column = "name"
        self.primary_key = "name"
        self.stack_name = stack["name"]
        super().__init__(*args, **kwargs)

    def determine_value(self, param):
        if param["ParameterValue"] == "*" * len(param["ParameterValue"]):
            return "<hidden>"
        return param["ParameterValue"]


class CFNOutputs(ResourceLister):
    prefix = "cfn_list"
    title = "CloudFormation Stack Outputs"

    def title_info(self):
        return self.stack_name

    def __init__(self, *args, stack=None, **kwargs):
        self.resource_key = "cloudformation"
        self.list_method = "describe_stacks"
        self.item_path = ".Stacks[0].Outputs"
        self.column_paths = {
            "name": ".OutputKey",
            "value": ".OutputValue",
        }
        self.list_kwargs = {"StackName": stack["name"]}
        self.imported_column_sizes = {
            "name": 30,
            "value": 30,
        }
        self.imported_column_order = ["name", "value"]

        self.sort_column = "name"
        self.primary_key = "name"
        self.stack_name = stack["name"]
        super().__init__(*args, **kwargs)
