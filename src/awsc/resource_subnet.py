from .base_control import Describer, ResourceLister
from .common import Common


class SubnetResourceLister(ResourceLister):
    prefix = "subnet_list"
    title = "Subnets"
    command_palette = ["subnet"]

    def title_info(self):
        if self.vpc is not None:
            return self.vpc["id"]
        elif self.db_subnet_group is not None:
            return self.db_subnet_group["name"]
        return None

    def __init__(self, *args, **kwargs):
        from .resource_routing import RouteTableResourceLister

        self.resource_key = "ec2"
        self.list_method = "describe_subnets"
        self.item_path = ".Subnets"
        if "vpc" in kwargs:
            self.vpc = kwargs["vpc"]
            self.list_kwargs = {
                "Filters": [
                    {
                        "Name": "vpc-id",
                        "Values": [
                            self.vpc["id"],
                        ],
                    }
                ]
            }
        else:
            self.vpc = None
        if "db_subnet_group" in kwargs:
            self.db_subnet_group = kwargs["db_subnet_group"]
            self.list_kwargs = self.get_db_subnet_ids
        else:
            self.db_subnet_group = None
        self.column_paths = {
            "id": ".SubnetId",
            "name": self.tag_finder_generator("Name"),
            "vpc": ".VpcId",
            "cidr": ".CidrBlock",
            "AZ": ".AvailabilityZone",
            "public": self.determine_public,
        }
        self.hidden_columns = {
            "arn": ".SubnetArn",
        }
        self.imported_column_sizes = {
            "id": 30,
            "name": 30,
            "vpc": 30,
            "cidr": 18,
            "AZ": 20,
            "public": 3,
        }
        self.describe_command = SubnetDescriber.opener
        self.additional_commands = {
            "t": {
                "command": RouteTableResourceLister.opener,
                "selection_arg": "subnet",
                "tooltip": "View Route Table",
            }
        }
        # self.open_command = RouteTableResourceLister.opener
        # self.open_selection_arg = 'subnet'

        self.imported_column_order = ["id", "name", "vpc", "cidr", "AZ", "public"]
        self.sort_column = "id"
        self.primary_key = "id"
        super().__init__(*args, **kwargs)

    def determine_public(self, subnet, *args):
        if subnet["MapPublicIpOnLaunch"]:
            return "✓"
        return ""

    def get_db_subnet_ids(self, *args):
        dsg_resp = Common.generic_api_call(
            "rds",
            "describe_db_subnet_groups",
            {"DBSubnetGroupName": self.db_subnet_group.name},
            "Describe DB Subnet Group",
            "RDS",
            subcategory="Subnet Group",
            resource=self.db_subnet_group.name,
        )
        if not dsg_resp["Success"]:
            return {"SubnetIds": []}
        dsg = dsg_resp["Response"]
        return {
            "SubnetIds": [
                s["SubnetIdentifier"] for s in dsg["DBSubnetGroups"][0]["Subnets"]
            ]
        }


class SubnetDescriber(Describer):
    prefix = "subnet_browser"
    title = "Subnet"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="id", **kwargs
    ):
        self.resource_key = "ec2"
        self.describe_method = "describe_subnets"
        self.describe_kwarg_name = "SubnetIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".Subnets[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
