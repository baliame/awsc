"""
Module for ELB v2 listener resources.
"""
from .arn import ARN
from .base_control import Describer, ResourceLister, ResourceRefByClass


class ListenerActionDescriber(Describer):
    """
    Describer control for listener rules.
    """

    prefix = "listener_action_browser"
    title = "Listener Rule"

    def __init__(self, *args, entry_key="arn", **kwargs):
        self.resource_key = "elbv2"
        self.describe_method = "describe_rules"
        self.describe_kwarg_name = "RuleArns"
        self.describe_kwarg_is_list = True
        self.object_path = ".Rules[0]"
        super().__init__(*args, entry_key=entry_key, **kwargs)


def _listener_action_determine_condition(result, *args):
    """
    Column callback for determining conditions on listener rules.
    """
    if len(result["Conditions"]) > 1:
        return "<multiple>"
    if len(result["Conditions"]) == 1:
        cond = result["Conditions"][0]
        field = cond["Field"]
        if field == "host-header":
            if "Values" in cond and cond["Values"]:
                if isinstance(cond["Values"], str):
                    return f"Host: {cond['Values']}"
                src = cond["Values"]
            else:
                src = cond["HostHeaderConfig"]["Values"]
            return f"Host: {'|'.join(src)}"
        if field == "path":
            if "Values" in cond and cond["Values"]:
                if isinstance(cond["Values"], str):
                    return f"Path: {cond['Values']}"
                src = cond["Values"]
            else:
                src = cond["PathPatternConfig"]["Values"]
            return f"Path: {'|'.join(src)}"

        return field
    return "<always>"


def _listener_action_determine_action_type(result, *args):
    """
    Column callback for determining types on listener rules.
    """
    if len(result["Actions"]) > 0:
        act = result["Actions"][-1]
        return act["Type"]
    return "N/A"


def _listener_action_determine_target(result, *args):
    """
    Column callback for determining targetss on listener rules.
    """
    if len(result["Actions"]) > 0:
        act = result["Actions"][-1]
        if act["Type"] == "forward":
            return ",".join(
                [
                    ARN(i["TargetGroupArn"]).resource_id_first
                    for i in act["ForwardConfig"]["TargetGroups"]
                ]
            )
        if act["Type"] == "redirect":
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
            port = f":{redirect['Port']}" if redirect["Port"] not in proto_ports else ""
            code = ("301" if redirect["StatusCode"] == "HTTP_301" else "302",)
            return f"{code} {proto}://{redirect['Host']}{port}{redirect['Path']}"
    return ""


class ListenerActionResourceLister(ResourceLister):
    """
    Lister control for listener rules.
    """

    prefix = "listener_action_list"
    title = "Listener Rules"

    resource_type = "listener rule"
    main_provider = "elbv2"
    category = "ELB v2"
    subcategory = "Listener Rules"
    list_method = "describe_rules"
    item_path = ".Rules"
    columns = {
        "priority": {
            "path": ".Priority",
            "size": 10,
            "weight": 0,
            "sort_weight": 0,
        },
        "condition": {
            "path": _listener_action_determine_condition,
            "size": 40,
            "weight": 1,
            "sort_weight": 1,
        },
        "action type": {
            "path": _listener_action_determine_action_type,
            "size": 20,
            "weight": 2,
            "sort_weight": 2,
        },
        "target": {
            "path": _listener_action_determine_target,
            "size": 120,
            "weight": 3,
            "sort_weight": 3,
        },
        "name": {"path": ".RuleArn", "hidden": True},
        "arn": {"path": ".RuleArn", "hidden": True},
    }
    primary_key = "arn"
    describe_command = ListenerActionDescriber.opener
    open_command = ResourceRefByClass("TargetGroupResourceLister")
    open_selection_arg = "rule_entry"

    def title_info(self):
        return self.listener["name"]

    def __init__(self, *args, listener, **kwargs):
        self.listener = listener
        self.list_kwargs = {"ListenerArn": self.listener["arn"]}
        super().__init__(*args, **kwargs)

    def open(self, *args):
        if self.selection is not None:
            if self.selection["action type"] == "forward":
                return super().open(*args)
            return self.describe(*args)
        return None


class ListenerDescriber(Describer):
    """
    Describer control for ELB v2 listeners.
    """

    prefix = "listener_browser"
    title = "Listener"

    def __init__(self, *args, **kwargs):
        self.resource_key = "elbv2"
        self.describe_method = "describe_listeners"
        self.describe_kwarg_name = "ListenerArns"
        self.describe_kwarg_is_list = True
        self.object_path = ".Listeners[0]"
        super().__init__(*args, **kwargs)


def _listener_determine_ssl_policy(self, result, *args):
    """
    Column callback which returns SSL Policy when it can exist.
    """
    if result["Protocol"] == "HTTPS":
        return result["SslPolicy"]
    return ""


class ListenerResourceLister(ResourceLister):
    """
    Lister control for ELB v2 listeners.
    """

    prefix = "listener_list"
    title = "Listeners"

    resource_type = "listener"
    main_provider = "elbv2"
    category = "ELB v2"
    subcategory = "Listeners"
    list_method = "describe_listeners"
    item_path = ".Listeners"
    columns = {
        "protocol": {
            "path": ".Protocol",
            "size": 10,
            "weight": 0,
            "sort_weight": 1,
        },
        "port": {"path": ".Port", "size": 10, "weight": 1, "sort_weight": 0},
        "instance type": {
            "path": _listener_determine_ssl_policy,
            "size": 20,
            "weight": 2,
        },
        "name": {"path": ".ListenerArn", "hidden": True},
        "arn": {"path": ".ListenerArn", "hidden": True},
    }
    primary_key = "arn"
    describe_command = ListenerDescriber.opener
    open_command = ListenerActionResourceLister.opener
    open_selection_arg = "listener"

    def title_info(self):
        return self.load_balancer["name"]

    def __init__(self, *args, lb, **kwargs):
        self.load_balancer = lb
        self.list_kwargs = {"LoadBalancerArn": self.load_balancer["arn"]}
        super().__init__(*args, **kwargs)
