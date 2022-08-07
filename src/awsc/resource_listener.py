from .arn import ARN
from .base_control import Describer, ResourceLister


class ListenerResourceLister(ResourceLister):
    prefix = "listener_list"
    title = "Listeners"

    def title_info(self):
        return self.load_balancer["name"]

    def __init__(self, *args, **kwargs):
        self.resource_key = "elbv2"
        self.list_method = "describe_listeners"
        self.item_path = ".Listeners"
        self.load_balancer = kwargs["lb"]
        self.list_kwargs = {"LoadBalancerArn": self.load_balancer["arn"]}
        self.column_paths = {
            "protocol": ".Protocol",
            "port": ".Port",
            "ssl policy": self.determine_ssl_policy,
        }
        self.imported_column_sizes = {
            "protocol": 10,
            "port": 10,
            "ssl policy": 30,
        }
        self.hidden_columns = {
            "arn": ".ListenerArn",
            "name": ".ListenerArn",
        }
        self.describe_command = ListenerDescriber.opener
        self.open_command = ListenerActionResourceLister.opener
        self.open_selection_arg = "listener"
        self.primary_key = "arn"

        self.imported_column_order = ["protocol", "port", "ssl policy"]
        self.sort_column = "arn"
        super().__init__(*args, **kwargs)

    def determine_ssl_policy(self, result, *args):
        if result["Protocol"] == "HTTPS":
            return result["SslPolicy"]
        return ""


class ListenerDescriber(Describer):
    prefix = "listener_browser"
    title = "Listener"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "elbv2"
        self.describe_method = "describe_listeners"
        self.describe_kwarg_name = "ListenerArns"
        self.describe_kwarg_is_list = True
        self.object_path = ".Listeners[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs,
        )


class ListenerActionResourceLister(ResourceLister):
    prefix = "listener_action_list"
    title = "Listener Rules"

    def title_info(self):
        return self.listener["name"]

    def __init__(self, *args, **kwargs):
        from .resource_tg import TargetGroupResourceLister

        self.resource_key = "elbv2"
        self.list_method = "describe_rules"
        self.item_path = ".Rules"
        self.listener = kwargs["listener"]
        self.list_kwargs = {"ListenerArn": self.listener["arn"]}
        self.column_paths = {
            "prio": ".Priority",
            "condition": self.determine_condition,
            "action type": self.determine_action_type,
            "target": self.determine_target,
        }
        self.imported_column_sizes = {
            "prio": 10,
            "condition": 40,
            "action type": 20,
            "target": 120,
        }
        self.hidden_columns = {
            "name": ".RuleArn",
            "arn": ".RuleArn",
        }
        self.describe_command = ListenerActionDescriber.opener
        self.open_command = TargetGroupResourceLister.opener
        self.open_selection_arg = "rule_entry"

        self.imported_column_order = ["prio", "condition", "action type", "target"]
        self.sort_column = "prio"
        super().__init__(*args, **kwargs)

    def open(self, *args):
        if self.selection is not None:
            if self.selection["action type"] == "forward":
                return super().open(*args)
            else:
                return self.describe(*args)

    def determine_condition(self, result, *args):
        if len(result["Conditions"]) > 1:
            return "<multiple>"
        elif len(result["Conditions"]) == 1:
            cond = result["Conditions"][0]
            field = cond["Field"]
            if field == "host-header":
                if "Values" in cond and len(cond["Values"]):
                    if isinstance(cond["Values"], str):
                        return f"Host: {cond['Values']}"
                    else:
                        src = cond["Values"]
                else:
                    src = cond["HostHeaderConfig"]["Values"]
                return f"Host: {'|'.join(src)}"
            elif field == "path":
                if "Values" in cond and len(cond["Values"]):
                    if isinstance(cond["Values"], str):
                        return f"Path: {cond['Values']}"
                    else:
                        src = cond["Values"]
                else:
                    src = cond["PathPatternConfig"]["Values"]
                return f"Path: {'|'.join(src)}"

            return field
        else:
            return "<always>"

    def determine_action_type(self, result, *args):
        if len(result["Actions"]) > 0:
            act = result["Actions"][-1]
            return act["Type"]
        else:
            return "N/A"

    def determine_target(self, result, *args):
        if len(result["Actions"]) > 0:
            act = result["Actions"][-1]
            if act["Type"] == "forward":
                return ",".join(
                    [
                        ARN(i["TargetGroupArn"]).resource_id_first
                        for i in act["ForwardConfig"]["TargetGroups"]
                    ]
                )
            elif act["Type"] == "redirect":
                redirect = act["RedirectConfig"]
                proto = (
                    "http(s)"
                    if redirect["Protocol"] == "#{protocol}"
                    else redirect["Protocol"].lower()
                )
                proto_ports = []
                if proto in ["http", "http(s)"]:
                    proto_ports.append("80")
                if proto in ["https", "http(s)"]:
                    proto_ports.append("443")
                port = (
                    f":{redirect['Port']}"
                    if redirect["Port"] not in proto_ports
                    else ""
                )
                code = ("301" if redirect["StatusCode"] == "HTTP_301" else "302",)
                return f"{code} {proto}://{redirect['Host']}{port}{redirect['Path']}"
        return ""


class ListenerActionDescriber(Describer):
    prefix = "listener_action_browser"
    title = "Listener Rule"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="arn", **kwargs
    ):
        self.resource_key = "elbv2"
        self.describe_method = "describe_rules"
        self.describe_kwarg_name = "RuleArns"
        self.describe_kwarg_is_list = True
        self.object_path = ".Rules[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs,
        )
