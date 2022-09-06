"""
Mdoule for controls related to load balanching.
"""
from .base_control import Describer, ResourceLister, ResourceRefByClass


class LBDescriber(Describer):
    """
    Describer control for v2 load balancers.
    """

    prefix = "lb_browser"
    title = "Load Balancer"

    def __init__(self, *args, **kwargs):
        self.resource_key = "elbv2"
        self.describe_method = "describe_load_balancers"
        self.describe_kwarg_name = "Names"
        self.describe_kwarg_is_list = True
        self.object_path = ".LoadBalancers[0]"
        super().__init__(*args, **kwargs)


def _elbv2_determine_scheme(result, *args):
    """
    Column callback for determining load balancer scheme.
    """
    if result["Scheme"] == "internet-facing":
        return "public"
    return "private"


class LBResourceLister(ResourceLister):
    """
    Lister control for v2 load balancers.
    """

    prefix = "lb_list"
    title = "Load Balancers"
    command_palette = ["lb", "elbv2", "loadbalancing"]

    resource_type = "load balancer"
    main_provider = "elbv2"
    category = "ELB v2"
    subcategory = "Load Balancer"
    list_method = "describe_load_balancers"
    item_path = ".LoadBalancers"
    columns = {
        "name": {
            "path": ".LoadBalancerName",
            "size": 30,
            "weight": 0,
            "sort_weight": 0,
        },
        "type": {"path": ".Type", "size": 15, "weight": 1},
        "scheme": {
            "path": _elbv2_determine_scheme,
            "size": 8,
            "weight": 2,
        },
        "hostname": {
            "path": ".DNSName",
            "size": 120,
            "weight": 3,
        },
        "arn": {"path": ".LoadBalancerArn", "hidden": True},
    }
    describe_command = LBDescriber.opener
    open_command = ResourceRefByClass("ListenerResourceLister")
    open_selection_arg = "lb"
