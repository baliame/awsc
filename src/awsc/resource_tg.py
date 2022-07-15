from .base_control import Describer, ResourceLister
from .common import Common


class TargetGroupResourceLister(ResourceLister):
    prefix = "target_group_list"
    title = "Target Groups"
    command_palette = ["tg", "targetgroup"]

    def title_info(self):
        if self.rule is not None:
            return self.rule["arn"]
        return None

    def __init__(self, *args, **kwargs):
        self.resource_key = "elbv2"
        self.list_method = "describe_target_groups"
        self.item_path = ".TargetGroups"
        if "rule_entry" in kwargs:
            self.rule = kwargs["rule_entry"]
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
        else:
            self.rule = None
        self.column_paths = {
            "name": ".TargetGroupName",
            "protocol": ".Protocol",
            "port": ".Port",
            "target type": ".TargetType",
        }
        self.imported_column_sizes = {
            "name": 30,
            "protocol": 10,
            "port": 10,
            "target type": 10,
        }
        self.hidden_columns = {
            "arn": ".TargetGroupArn",
        }
        self.describe_command = TargetGroupDescriber.opener
        # self.open_command = ListenerActionResourceLister.opener
        # self.open_selection_arg = 'listener'

        self.imported_column_order = ["name", "protocol", "port", "target type"]
        self.sort_column = "name"
        self.primary_key = "arn"
        super().__init__(*args, **kwargs)


class TargetGroupDescriber(Describer):
    prefix = "tg_browser"
    title = "Target Group"

    def populate_entry(self, *args, entry, **kwargs):
        super().populate_entry(*args, entry=entry, **kwargs)
        try:
            self.name = entry["name"]
        except KeyError:
            self.name = self.entry_id

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="arn", **kwargs
    ):
        self.resource_key = "elbv2"
        self.describe_method = "describe_target_groups"
        self.describe_kwarg_name = "TargetGroupArns"
        self.describe_kwarg_is_list = True
        self.object_path = ".TargetGroups[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )

    def title_info(self):
        return self.name
