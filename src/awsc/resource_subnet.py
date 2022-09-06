"""
Module for subnet resources.
"""
from .base_control import Describer, ResourceLister, tagged_column_generator
from .common import Common


class SubnetDescriber(Describer):
    """
    Describer control for subnet resources.
    """

    prefix = "subnet_browser"
    title = "Subnet"

    def __init__(self, *args, entry_key="id", **kwargs):
        self.resource_key = "ec2"
        self.describe_method = "describe_subnets"
        self.describe_kwarg_name = "SubnetIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".Subnets[0]"
        super().__init__(*args, entry_key=entry_key, **kwargs)


def _subnet_determine_public(self, subnet, *args):
    if subnet["MapPublicIpOnLaunch"]:
        return "✓"
    return ""


@ResourceLister.Autocommand("VPCResourceLister", "t", "View Subnets", "vpc")
@ResourceLister.Autocommand(
    "DBSubnetGroupResourceLister", "t", "View Subnets", "db_subnet_group"
)
class SubnetResourceLister(ResourceLister):
    """
    Lister control for subnet resources.
    """

    prefix = "subnet_list"
    title = "Subnets"
    command_palette = ["subnet"]

    resource_type = "Subnet"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "Subnet"
    list_method = "describe_subnets"
    item_path = ".Subnets"
    columns = {
        "id": {"path": ".SubnetId", "size": 30, "weight": 0},
        **tagged_column_generator("name", "name", weight=1, sort_weight=2, size=30),
        "vpc": {"path": ".VpcId", "size": 30, "weight": 2, "sort_weight": 0},
        "cidr": {"path": ".CidrBlock", "size": 18, "weight": 3, "sort_weight": 1},
        "AZ": {"path": ".AvailabilityZone", "size": 20, "weight": 4},
        "public": {"path": _subnet_determine_public, "size": 3, "weight": 5},
        "arn": {"path": ".SubnetArn", "hidden": True},
    }
    describe_command = SubnetDescriber.opener
    primary_key = "id"

    def title_info(self):
        if self.vpc is not None:
            return self.vpc["id"]
        if self.db_subnet_group is not None:
            return self.db_subnet_group["name"]
        return None

    def __init__(self, *args, vpc=None, db_subnet_group=None, **kwargs):
        self.vpc = vpc
        self.db_subnet_group = db_subnet_group
        if vpc is not None:
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
        if db_subnet_group is not None:
            self.list_kwargs = self.get_db_subnet_ids()
        super().__init__(*args, **kwargs)

    def get_db_subnet_ids(self, *args):
        """
        Generates a filetr for listing subnets based on a DB subnet group.

        Returns
        -------
        dict
            A filter to pass to list_kwargs for filtering for the DB subnet group in self.db_subnet_group.
        """
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
