"""
Module for cloudwatch resources.
"""

import datetime


from .base_control import (
    Describer,
    ListResourceDocumentEditor,
    OpenableListControl,
    ResourceLister,
    SelectionAttribute,
)
from .common import BaseChart, Common, SessionAwareDialog
from .dashboard import KeyValueDashboardBlock
from .termui.list_control import ListEntry
from .termui.ui import ControlCodes

def _cwlogs_object_determine_size(entry, **kwargs):
    if "Prefix" in entry:
        return ""
    return Common.human_readable_size(entry["size"])


class LogInsightQueryDialog(SessionAwareDialog):
    """
    Custom dialog for running a Log Insights query.
    """

    line_size = 15

    def __init__(
        self,
        *args,
        instance_entry=None,
        caller=None,
        **kwargs,
    ):
        kwargs["border"] = Border(
            Common.border("ec2_ssh", "default"),
            Common.color("ec2_ssh_modal_dialog_border", "modal_dialog_border"),
            "Log Insights Query",
            Common.color(
                "ec2_ssh_modal_dialog_border_title", "modal_dialog_border_title"
            ),
            instance_entry["instance id"],
            Common.color(
                "ec2_ssh_modal_dialog_border_title_info",
                "modal_dialog_border_title_info",
            ),
        )
        super().__init__(*args, caller=caller, **kwargs)
        self.set_title_label("Connect to EC2 over SSH")
        self.instance_id = instance_entry["instance id"]
        self.ip = instance_entry["public ip"]
        def_text = (
            Common.Configuration["default_ssh_usernames"][Common.Session.ssh_key]
            if Common.Session.ssh_key in Common.Configuration["default_ssh_usernames"]
            else ""
        )
        self.username_textfield = DialogFieldText(
            "SSH username",
            text=def_text,
            **Common.textfield_colors("ec2_ssh"),
        )
        self.add_field(self.use_instance_connect)
        self.add_field(self.username_textfield)
        self.highlighted = 0
        self.caller = caller


class LogGroupDescriber(Describer):
    """
    Describer control for AWS Secrets Manager secrets.
    """

    prefix = "log_group_browser"
    title = "Log Group"

    resource_type = "log_group"
    main_provider = "logs"
    category = "Cloudwatch"
    subcategory = "Logs"
    describe_method = "describe_log_groups"
    describe_kwarg_name = "logGroupNamePrefix"
    object_path = "."

class LogGroupLister(ResourceLister):
    """
    Lister resource for Cloudwatch Log Groups.
    """

    prefix = "log_group_list"
    title = "Log Groups"

    resource_type = "log_group"
    main_provider = "logs"
    category = "Cloudwatch"
    subcategory = "Logs"
    list_method = "describe_log_groups"
    item_path = ".logGroups"
    columns = {
        "name": {"path": ".logGroupName", "size": 64, "weight": 0, "sort_weight": 0},
        "retentionDays": {"path": ".retentionInDays", "size": 8, "weight": 1},
        "size": {"path": _cwlogs_object_determine_size, "size": 16, "weight": 2}
    }
    describe_command = LogGroupDescriber.opener
    #open_command = MetricViewer.opener
    #open_selection_arg = "metric"

    def __init__(
        self, *args, dimension, metric_namespace=None, metric_name=None, **kwargs
    ):
        self.dimension = dimension
        self.list_kwargs = {}
        if metric_namespace is not None:
            self.list_kwargs["Namespace"] = metric_namespace
        if metric_name is not None:
            self.list_kwargs["MetricName"] = metric_name
        super().__init__(*args, **kwargs)
