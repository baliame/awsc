"""
Module for VPC routing resources.
"""
import json

from .base_control import (
    Describer,
    GenericDescriber,
    ResourceLister,
    tagged_column_generator,
)
from .common import Common


def _route_determine_gateway_type(self, entry):
    """
    Column callback for determining the type of a gateway at the tail end of a route.
    """
    if "NatGatewayId" in entry:
        return "NAT"
    if "InstanceId" in entry:
        return "Instance"
    if "TransitGatewayId" in entry:
        return "Transit"
    if "LocalGatewayId" in entry:
        return "Local"
    if "CarrierGatewayId" in entry:
        return "Carrier"
    if "VpcPeeringConnectionId" in entry:
        return "VPC Peering"
    if "EgressOnlyInternetGatewayId" in entry:
        return "Egress-Only"
    if entry["GatewayId"] == "local":
        return "VPC-Local"
    return "Internet"


def _route_determine_gateway(self, entry):
    """
    Column callback for determining the gateway ID at the tail end of a route.
    """
    if "NatGatewayId" in entry:
        return entry["NatGatewayId"]
    if "InstanceId" in entry:
        return entry["InstanceId"]
    if "TransitGatewayId" in entry:
        return entry["TransitGatewayId"]
    if "LocalGatewayId" in entry:
        return entry["LocalGatewayId"]
    if "CarrierGatewayId" in entry:
        return entry["CarrierGatewayId"]
    if "VpcPeeringConnectionId" in entry:
        return entry["VpcPeeringConnectionId"]
    if "EgressOnlyInternetGatewayId" in entry:
        return entry["EgressOnlyInternetGatewayId"]
    return entry["GatewayId"]


class RouteResourceLister(ResourceLister):
    """
    Lister control for VPC route resources.
    """

    prefix = "route_list"
    title = "Routes"
    command_palette = ["route"]

    resource_type = "route"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "VPC Route"
    list_method = "describe_route_tables"
    item_path = "[.RouteTables[] as $rt | $rt.Routes[] as $r | $r | .RouteTableId = $rt.RouteTableId]"
    columns = {
        "route table": {
            "path": ".RouteTableId",
            "size": 30,
            "weight": 0,
            "sort_weight": 0,
        },
        "gateway type": {
            "path": _route_determine_gateway_type,
            "size": 20,
            "weight": 1,
            "sort_weight": 1,
        },
        "gateway": {
            "path": _route_determine_gateway,
            "size": 30,
            "weight": 2,
        },
        "destination": {
            "path": ".DestinationCidrBlock",
            "size": 30,
            "weight": 3,
        },
        "state": {
            "path": ".State",
            "size": 10,
            "weight": 4,
        },
        "name": {
            "path": lambda _: "",
            "hidden": True,
        },
    }
    primary_key = None

    def title_info(self):
        if self.route_table is not None:
            return self.route_table["id"]
        return None

    def __init__(self, *args, route_table=None, **kwargs):
        if route_table is not None:
            self.route_table = route_table
            self.list_kwargs = {"RouteTableIds": [self.route_table["id"]]}
        super().__init__(*args, **kwargs)

    @ResourceLister.Autohotkey("d", "Describe", True)
    @ResourceLister.Autohotkey("KEY_ENTER", "Describe", True)
    def generic_describe(self, entry):
        """
        Custom describer for routes. We're inventing our own description here, AWS provides none.
        """
        Common.Session.push_frame(
            GenericDescriber.opener(
                **{
                    "describing": f"Route in route table {self.selection['route table']}",
                    "content": json.dumps(
                        self.selection.controller_data, sort_keys=True, indent=2
                    ),
                    "pushed": True,
                }
            )
        )


class RouteTableDescriber(Describer):
    """
    Describer control for VPC route tables.
    """

    prefix = "route_table_browser"
    title = "Route Table"

    def __init__(self, *args, entry_key="id", **kwargs):
        self.resource_key = "ec2"
        self.describe_method = "describe_route_tables"
        self.describe_kwarg_name = "RouteTableIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".RouteTables[0]"
        super().__init__(*args, entry_key=entry_key, **kwargs)


def _route_table_determine_subnet_association(self, result, *args):
    if "Associations" not in result or len(result["Associations"]) == 0:
        return "<none>"
    if len(result["Associations"]) > 1:
        return "<multiple>"
    if "SubnetId" in result["Associations"][0]:
        return result["Associations"][0]["SubnetId"]
    return "<VPC default>"


@ResourceLister.Autocommand("SubnetResourceLister", "t", "View Route Table", "subnet")
class RouteTableResourceLister(ResourceLister):
    """
    Lister control for VPC route tables.
    """

    prefix = "route_table_list"
    title = "Route Tables"
    command_palette = ["rt", "routetable"]

    resource_type = "route table"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "VPC Route Table"
    list_method = "describe_route_tables"
    item_path = ".RouteTables"
    columns = {
        "id": {
            "path": ".RouteTableId",
            "size": 30,
            "weight": 0,
            "sort_weight": 1,
        },
        **tagged_column_generator("name", "name", weight=1, sort_weight=0, size=30),
        "vpc": {
            "path": ".VpcId",
            "size": 30,
            "weight": 2,
        },
        "type": {
            "path": _route_table_determine_subnet_association,
            "size": 30,
            "weight": 3,
        },
    }
    primary_key = "id"
    describe_command = RouteTableDescriber.opener
    open_command = RouteResourceLister.opener
    open_selection_arg = "route_table"

    def title_info(self):
        return self.subnet["id"] if self.subnet is not None else None

    def __init__(self, *args, subnet=None, **kwargs):
        self.subnet = subnet
        if subnet is not None:
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
        super().__init__(*args, **kwargs)
