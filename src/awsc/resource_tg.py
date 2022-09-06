"""
Module for ELBv2 Target Group resources.
"""
from .base_control import Describer, ResourceLister
from .common import Common


class TargetGroupDescriber(Describer):
    """
    Describer control for ELBv2 Target Groups.
    """

    prefix = "tg_browser"
    title = "Target Group"

    def populate_entry(self, *args, entry, **kwargs):
        super().populate_entry(*args, entry=entry, **kwargs)
        try:
            self.name = entry["name"]
        except KeyError:
            self.name = self.entry_id

    def __init__(self, *args, entry_key="arn", **kwargs):
        self.resource_key = "elbv2"
        self.describe_method = "describe_target_groups"
        self.describe_kwarg_name = "TargetGroupArns"
        self.describe_kwarg_is_list = True
        self.object_path = ".TargetGroups[0]"
        super().__init__(*args, entry_key=entry_key, **kwargs)

    def title_info(self):
        return self.name


class TargetGroupResourceLister(ResourceLister):
    """
    Lister control for ELBv2 Target Groups.
    """

    prefix = "target_group_list"
    title = "Target Groups"
    command_palette = ["tg", "targetgroup"]

    resource_type = "target group"
    main_provider = "elbv2"
    category = "ELB v2"
    subcategory = "Target Group"
    list_method = "describe_target_groups"
    item_path = ".TargetGroups"
    columns = {
        "name": {
            "path": ".TargetGroupName",
            "size": 30,
            "weight": 0,
            "sort_weight": 0,
        },
        "protocol": {"path": ".Protocol", "size": 10, "weight": 1},
        "port": {"path": ".Port", "size": 10, "weight": 2},
        "target type": {"path": ".TargetType", "size": 10, "weight": 3},
        "arn": {"path": ".TargetGroupArn", "hidden": True},
    }
    describe_command = TargetGroupDescriber.opener
    primary_key = "arn"

    def title_info(self):
        return self.rule["arn"] if self.rule is not None else None

    def __init__(self, *args, rule_entry=None, **kwargs):
        self.rule = rule_entry
        if rule_entry is not None:
            arns = []
            raw = self.rule.controller_data
            try:
                arns = [
                    i["TargetGroupArn"]
                    for i in raw["Actions"][-1]["ForwardConfig"]["TargetGroups"]
                ]
                self.list_kwargs = {"TargetGroupArns": arns}
            except KeyError:
                self.rule = None
                Common.Session.set_message(
                    "Rule is not configured for forwarding.",
                    Common.color("message_error"),
                )
        super().__init__(*args, **kwargs)
