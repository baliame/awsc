import json

from .base_control import Describer, GenericDescriber, ResourceLister
from .common import Common


class RouteTableResourceLister(ResourceLister):
    prefix = "route_table_list"
    title = "Route Tables"
    command_palette = ["rt", "routetable"]

    def title_info(self):
        if self.subnet is not None:
            return self.subnet["id"]
        return None

    def __init__(self, *args, **kwargs):
        self.resource_key = "ec2"
        self.list_method = "describe_route_tables"
        self.item_path = ".RouteTables"
        if "subnet" in kwargs:
            self.subnet = kwargs["subnet"]
            self.list_kwargs = {
                "Filters": [
                    {
                        "Name": "association.subnet-id",
                        "Values": [
                            self.subnet["id"],
                        ],
                    }
                ]
            }
        else:
            self.subnet = None
        self.column_paths = {
            "id": ".RouteTableId",
            "name": self.tag_finder_generator("Name"),
            "vpc": ".VpcId",
            "subnet": self.determine_subnet_association,
        }
        self.imported_column_sizes = {
            "id": 30,
            "name": 30,
            "vpc": 30,
            "subnet": 30,
        }
        self.describe_command = RouteTableDescriber.opener
        self.open_command = RouteResourceLister.opener
        self.open_selection_arg = "route_table"

        self.imported_column_order = ["id", "name", "vpc", "subnet"]
        self.sort_column = "id"
        self.primary_key = "id"
        super().__init__(*args, **kwargs)

    def determine_subnet_association(self, rt, *args):
        if "Associations" not in rt or len(rt["Associations"]) == 0:
            return "<none>"
        if len(rt["Associations"]) > 1:
            return "<multiple>"
        if "SubnetId" in rt["Associations"][0]:
            return rt["Associations"][0]["SubnetId"]
        else:
            return "<VPC default>"


class RouteTableDescriber(Describer):
    prefix = "route_table_browser"
    title = "Route Table"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="id", **kwargs
    ):
        self.resource_key = "ec2"
        self.describe_method = "describe_route_tables"
        self.describe_kwarg_name = "RouteTableIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".RouteTables[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


# Routes
class RouteResourceLister(ResourceLister):
    prefix = "route_list"
    title = "Routes"
    command_palette = ["route"]

    def title_info(self):
        if self.route_table is not None:
            return self.route_table["id"]
        return None

    def __init__(self, *args, **kwargs):
        self.resource_key = "ec2"
        self.list_method = "describe_route_tables"
        self.item_path = "[.RouteTables[] as $rt | $rt.Routes[] as $r | $r | .RouteTableId = $rt.RouteTableId]"
        if "route_table" in kwargs:
            self.route_table = kwargs["route_table"]
            self.list_kwargs = {"RouteTableIds": [self.route_table["id"]]}
        else:
            self.route_table = None
        self.column_paths = {
            "route table": ".RouteTableId",
            "gateway type": self.determine_gateway_type,
            "gateway": self.determine_gateway,
            "destination": ".DestinationCidrBlock",
            "state": ".State",
        }
        self.hidden_columns = {
            "name": self.empty,
        }
        self.imported_column_sizes = {
            "route table": 30,
            "gateway type": 20,
            "gateway": 30,
            "destination": 30,
            "state": 10,
        }

        self.imported_column_order = [
            "route table",
            "gateway type",
            "gateway",
            "destination",
            "state",
        ]
        self.sort_column = "route table"
        self.primary_key = None
        super().__init__(*args, **kwargs)

        self.add_hotkey("d", self.generic_describe, "Describe")
        self.add_hotkey("KEY_ENTER", self.generic_describe, "Describe")

    def generic_describe(self, entry):
        if self.selection is not None:
            Common.Session.push_frame(
                GenericDescriber.opener(
                    **{
                        "describing": "Route in route table {0}".format(
                            self.selection["route table"]
                        ),
                        "content": json.dumps(
                            self.selection.controller_data, sort_keys=True, indent=2
                        ),
                        "pushed": True,
                    }
                )
            )

    def determine_gateway_type(self, entry):
        if "NatGatewayId" in entry:
            return "NAT"
        elif "InstanceId" in entry:
            return "Instance"
        elif "TransitGatewayId" in entry:
            return "Transit"
        elif "LocalGatewayId" in entry:
            return "Local"
        elif "CarrierGatewayId" in entry:
            return "Carrier"
        elif "VpcPeeringConnectionId" in entry:
            return "VPC Peering"
        elif "EgressOnlyInternetGatewayId" in entry:
            return "Egress-Only"
        elif entry["GatewayId"] == "local":
            return "VPC-Local"
        else:
            return "Internet"

    def determine_gateway(self, entry):
        if "NatGatewayId" in entry:
            return entry["NatGatewayId"]
        elif "InstanceId" in entry:
            return entry["InstanceId"]
        elif "TransitGatewayId" in entry:
            return entry["TransitGatewayId"]
        elif "LocalGatewayId" in entry:
            return entry["LocalGatewayId"]
        elif "CarrierGatewayId" in entry:
            return entry["CarrierGatewayId"]
        elif "VpcPeeringConnectionId" in entry:
            return entry["VpcPeeringConnectionId"]
        elif "EgressOnlyInternetGatewayId" in entry:
            return entry["EgressOnlyInternetGatewayId"]
        else:
            return entry["GatewayId"]
