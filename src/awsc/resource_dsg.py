"""
Module for database subnet groups.
"""
from .base_control import Describer, ResourceLister


class DBSubnetGroupDescriber(Describer):
    """
    Describer control for database subnets.
    """

    prefix = "db_subnet_group_browser"
    title = "DB Subnet Group"

    resource_type = "db subnet group"
    main_provider = "rds"
    category = "RDS"
    subcategory = "DB Subnet Groups"
    describe_method = "describe_db_subnet_groups"
    describe_kwarg_name = "DBSubnetGroupName"
    describe_kwarg_is_list = True
    object_path = ".DBSubnetGroups[0]"


class DBSubnetGroupResourceLister(ResourceLister):
    """
    Lister control for database subnets.
    """

    prefix = "db_subnet_group_list"
    title = "DB Subnet Groups"
    command_palette = ["dsg", "dbsubnetgroup"]

    resource_type = "db subnet group"
    main_provider = "rds"
    category = "RDS"
    subcategory = "DB Subnet Groups"
    list_method = "describe_db_subnet_groups"
    item_path = ".DBSubnetGroups"
    columns = {
        "vpc": {"path": ".VpcId", "size": 30, "weight": 0, "sort_weight": 0},
        "name": {
            "path": ".DBSubnetGroupName",
            "size": 30,
            "weight": 1,
            "sort_weight": 1,
        },
        "status": {"path": ".SubnetGroupStatus", "size": 30, "weight": 2},
    }
    describe_command = DBSubnetGroupDescriber.opener
    open_command = "t"
