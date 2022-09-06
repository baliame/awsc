"""
Module for VPC resources.
"""
from .base_control import Describer, ResourceLister, tagged_column_generator


class VPCDescriber(Describer):
    """
    Describer control for VPC resources.
    """

    prefix = "vpc_browser"
    title = "VPC"

    def __init__(self, *args, entry_key="id", **kwargs):
        self.resource_key = "ec2"
        self.describe_method = "describe_vpcs"
        self.describe_kwarg_name = "VpcIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".Vpcs[0]"
        super().__init__(*args, entry_key=entry_key, **kwargs)


def _vpc_determine_default(self, vpc, *args):
    if vpc["IsDefault"]:
        return "✓"
    return ""


class VPCResourceLister(ResourceLister):
    """
    Lister control for VPC resources.
    """

    prefix = "vpc_list"
    title = "VPCs"
    command_palette = ["vpc"]

    resource_type = "vpc"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "VPC"
    list_method = "describe_vpcs"
    item_path = ".Vpcs"
    columns = {
        "id": {
            "path": ".VpcId",
            "size": 30,
            "weight": 0,
            "sort_weight": 1,
        },
        **tagged_column_generator("name", "name", weight=1, sort_weight=0, size=30),
        "default": {
            "path": _vpc_determine_default,
            "size": 3,
            "weight": 2,
        },
        "cidr": {
            "path": ".CidrBlock",
            "size": 18,
            "weight": 3,
        },
        "state": {
            "path": ".State",
            "size": 9,
            "weight": 4,
        },
        # "arn": {"path": ".SubnetArn", "hidden": True},
    }
    describe_command = VPCDescriber.opener
    open_command = "t"
    primary_key = "id"
