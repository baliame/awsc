from .base_control import Describer, ResourceLister


class DBSubnetGroupResourceLister(ResourceLister):
    prefix = "db_subnet_group_list"
    title = "DB Subnet Groups"
    command_palette = ["dsg", "dbsubnetgroup"]

    def __init__(self, *args, **kwargs):
        from .resource_subnet import SubnetResourceLister

        self.resource_key = "rds"
        self.list_method = "describe_db_subnet_groups"
        self.item_path = ".DBSubnetGroups"
        self.column_paths = {
            "name": ".DBSubnetGroupName",
            "vpc": ".VpcId",
            "status": ".SubnetGroupStatus",
        }
        self.hidden_columns = {
            "arn": ".DBSubnetGroupArn",
        }
        self.imported_column_sizes = {
            "name": 30,
            "vpc": 30,
            "status": 30,
        }
        self.describe_command = DBSubnetGroupDescriber.opener
        self.open_command = SubnetResourceLister.opener
        self.open_selection_arg = "db_subnet_group"
        self.primary_key = "name"

        self.imported_column_order = ["name", "vpc", "status"]
        self.sort_column = "name"
        super().__init__(*args, **kwargs)


class DBSubnetGroupDescriber(Describer):
    prefix = "subnet_browser"
    title = "Subnet"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "rds"
        self.describe_method = "describe_db_subnet_groups"
        self.describe_kwarg_name = "DBSubnetGroupName"
        self.describe_kwarg_is_list = True
        self.object_path = ".DBSubnetGroups[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
