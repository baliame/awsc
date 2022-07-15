from .base_control import Describer, ResourceLister


class VPCResourceLister(ResourceLister):
    prefix = "vpc_list"
    title = "VPCs"
    command_palette = ["vpc"]

    def __init__(self, *args, **kwargs):
        from .resource_subnet import SubnetResourceLister

        self.resource_key = "ec2"
        self.list_method = "describe_vpcs"
        self.item_path = ".Vpcs"
        self.column_paths = {
            "id": ".VpcId",
            "name": self.tag_finder_generator("Name"),
            "default": self.determine_default,
            "cidr": ".CidrBlock",
            "state": ".State",
        }
        self.imported_column_sizes = {
            "id": 30,
            "name": 30,
            "default": 3,
            "cidr": 18,
            "state": 9,
        }
        self.describe_command = VPCDescriber.opener
        self.additional_commands = {
            "t": {
                "command": SubnetResourceLister.opener,
                "selection_arg": "vpc",
                "tooltip": "View Subnets",
            }
        }
        self.open_command = "t"

        self.imported_column_order = ["id", "name", "default", "cidr", "state"]
        self.sort_column = "id"
        self.primary_key = "id"
        super().__init__(*args, **kwargs)

    def determine_default(self, vpc, *args):
        if vpc["IsDefault"]:
            return "✓"
        return ""


class VPCDescriber(Describer):
    prefix = "vpc_browser"
    title = "VPC"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="id", **kwargs
    ):
        self.resource_key = "ec2"
        self.describe_method = "describe_vpcs"
        self.describe_kwarg_name = "VpcIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".Vpcs[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
