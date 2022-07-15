from .base_control import Describer, ResourceLister


class LBResourceLister(ResourceLister):
    prefix = "lb_list"
    title = "Load Balancers"
    command_palette = ["lb", "elbv2", "loadbalancing"]

    def __init__(self, *args, **kwargs):
        from .resource_listener import ListenerResourceLister

        self.resource_key = "elbv2"
        self.list_method = "describe_load_balancers"
        self.item_path = ".LoadBalancers"
        self.column_paths = {
            "name": ".LoadBalancerName",
            "type": ".Type",
            "scheme": self.determine_scheme,
            "hostname": ".DNSName",
        }
        self.imported_column_sizes = {
            "name": 30,
            "type": 15,
            "scheme": 8,
            "hostname": 120,
        }
        self.hidden_columns = {
            "arn": ".LoadBalancerArn",
        }
        self.describe_command = LBDescriber.opener
        self.open_command = ListenerResourceLister.opener
        self.open_selection_arg = "lb"

        self.imported_column_order = ["name", "type", "scheme", "hostname"]
        self.sort_column = "name"
        self.primary_key = "name"
        super().__init__(*args, **kwargs)

    def determine_scheme(self, lb, *args):
        if lb["Scheme"] == "internet-facing":
            return "public"
        return "private"


class LBDescriber(Describer):
    prefix = "lb_browser"
    title = "Load Balancer"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "elbv2"
        self.describe_method = "describe_load_balancers"
        self.describe_kwarg_name = "Names"
        self.describe_kwarg_is_list = True
        self.object_path = ".LoadBalancers[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
