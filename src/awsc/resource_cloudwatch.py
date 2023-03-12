"""
Module for cloudwatch resources.
"""
import datetime

from .base_control import (
    Describer,
    ListResourceDocumentEditor,
    ResourceLister,
    SelectionAttribute,
)
from .common import BaseChart, Common
from .dashboard import KeyValueDashboardBlock
from .termui.ui import ControlCodes


class MetricViewer(BaseChart):
    """
    Metric display control. Displays the selected metric as a bar graph.
    """

    prefix = "metric_view"
    title = "Metrics"

    def title_info(self):
        return f"{self.metric_dimension['Value']} {self.metric_name}"

    def __init__(self, *args, caller, metric=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.metric_name = metric["name"]
        self.metric_namespace = metric["namespace"]
        self.metric_dimension = {
            "Name": caller.dimension[0],
            "Value": caller.dimension[1],
        }
        self.load_data()

    def load_data(self):
        """
        Loads time series into the bar graph based on the metric name, namespace and dimension provided.
        """
        api_kwargs = {
            "MetricDataQueries": [
                {
                    "Id": "metric",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": self.metric_namespace,
                            "MetricName": self.metric_name,
                            "Dimensions": [self.metric_dimension],
                        },
                        "Period": 300,
                        "Stat": "Average",
                    },
                }
            ],
            "StartTime": datetime.datetime.now() - datetime.timedelta(hours=24),
            "EndTime": datetime.datetime.now(),
        }
        call = Common.generic_api_call(
            "cloudwatch",
            "get_metric_data",
            api_kwargs,
            "Retrieve metrics",
            "Cloudwatch",
            subcategory="Metrics",
            resource=f"{self.metric_namespace}/{self.metric_name}",
        )
        if call["Success"]:
            data = call["Response"]
            for idx in range(len(data["MetricDataResults"][0]["Timestamps"])):
                timestamp = data["MetricDataResults"][0]["Timestamps"][idx]
                value = data["MetricDataResults"][0]["Values"][idx]
                self.add_datapoint(timestamp, value)


class MetricLister(ResourceLister):
    """
    Lister resource for Cloudwatch Metrics.
    """

    prefix = "metric_list"
    title = "Metrics"

    resource_type = "metric"
    main_provider = "cloudwatch"
    category = "Cloudwatch"
    subcategory = "Metrics"
    list_method = "list_metrics"
    item_path = ".Metrics"
    columns = {
        "namespace": {"path": ".Namespace", "size": 16, "weight": 0, "sort_weight": 0},
        "name": {"path": ".MetricName", "size": 64, "weight": 1, "sort_weight": 1},
    }
    open_command = MetricViewer.opener
    open_selection_arg = "metric"

    def title_info(self):
        return f"{self.dimension[0]}={self.dimension[1]}"

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


class AlarmDescriber(Describer):
    """
    Describer resource for Cloudwatch Alarms.
    """

    prefix = "alarm_browser"
    title = "Cloudwatch Alarm"

    resource_type = "alarm"
    main_provider = "cloudwatch"
    category = "Cloudwatch"
    subcategory = "Alarm"
    describe_method = "describe_alarms"

    def __init__(self, *args, entry, **kwargs):
        self.resource_key = "cloudwatch"
        self.describe_kwargs = {
            "AlarmNames": [entry["name"]],
            "AlarmTypes": [f"{entry['type']}Alarm"],
        }
        self.object_path = (
            ".CompositeAlarms[0]"
            if entry["type"] == "Composite"
            else ".MetricAlarms[0]"
        )
        super().__init__(*args, entry=entry, **kwargs)


class AlarmLister(ResourceLister):
    """
    Lister resource for Cloudwatch Alarms.
    """

    prefix = "alarm_list"
    title = "Cloudwatch Alarms"
    command_palette = ["alarm", "cloudwatchalarm"]

    resource_type = "alarm"
    main_provider = "cloudwatch"
    category = "Cloudwatch"
    subcategory = "Alarms"
    list_method = "describe_alarms"
    item_path = ".CompositeAlarms + .MetricAlarms"
    columns = {
        "name": {"path": ".AlarmName", "size": 10, "weight": 0, "sort_weight": 0},
        "type": {
            "path": lambda x: "Metric"
            if "MetricName" in x or "Metrics" in x
            else "Composite",
            "size": 10,
            "weight": 1,
        },
        "actions": {
            "path": lambda x: "Enabled" if x["ActionsEnabled"] else "Disabled",
            "size": 10,
            "weight": 2,
        },
        "state": {"path": ".StateValue", "size": 10, "weight": 3},
        "description": {
            "path": ".AlarmDescription",
            "size": 64,
            "weight": 4,
        },
        "arn": {"path": ".AlarmArn", "hidden": True},
    }
    describe_command = AlarmDescriber.opener

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.confirm_template(
            "delete_alarms",
            {"AlarmNames": [SelectionAttribute("name")]},
            hotkey=ControlCodes.D,
            hotkey_tooltip="Delete alarm",
        )

    @ResourceLister.Autohotkey("e", "Edit", True)
    def edit(self, _):
        """
        Hotkey callback for editing a cloudwatch alarm.
        """
        editor = ListResourceDocumentEditor(
            "cloudwatch",
            "describe_alarms",
            ".CompositeAlarms[0]"
            if self.selection["type"] == "Composite"
            else ".MetricAlarms[0]",
            "put_composite_alarm"
            if self.selection["type"] == "Composite"
            else "put_metric_alarm",
            "AlarmNames",
            update_document_arg=None,
            entry_name_is_list=True,
            entry_key="name",
            entry_name_arg_update=None,
            as_json=True,
            message="Update successful",
            ignored_fields=[
                "AlarmArn",
                "AlarmConfigurationUpdatedTimestamp",
                "StateValue",
                "StateReason",
                "StateReasonData",
                "StateUpdatedTimestamp",
                "ActionsSuppressedReason",
                "ActionsSuppressedBy",
                "AlarmName",
            ],
            static_fields={"AlarmName": self.selection["name"]},
        )
        editor.edit(self.selection)


class CloudwatchAlarmDashboardBlock(KeyValueDashboardBlock):
    """
    Dashboard block for Cloudwatch Alarms.
    """

    description = "Cloudwatch Alarm summary"

    labels = {
        "total": "Total alarms",
        "OK": "Alarms in OK state",
        "ALARM": "Alarms in ALARM state",
        "INSUFFICIENT_DATA": "Alarms in INSUFFICIENT_DATA state",
    }
    thresholds = {
        "ALARM": [
            "dashboard_block_positive",
            1,
            "dashboard_block_negative",
        ],
        "INSUFFICIENT_DATA": [
            "dashboard_block_positive",
            1,
            "dashboard_block_neutral",
        ],
    }
    order = [
        "total",
        "OK",
        "ALARM",
        "INSUFFICIENT_DATA",
    ]

    def __init__(self, *args, **kwargs):
        self.alarm_data = {}
        super().__init__(*args, **kwargs)

    def refresh_data(self):
        resp = Common.generic_api_call(
            "cloudwatch",
            "describe_alarms",
            {},
            "Describe alarms",
            "Cloudwatch",
            subcategory="Alarm",
        )
        if resp["Success"]:
            asd = resp["Response"]
            info = {}
            info["total"] = len(asd["CompositeAlarms"]) + len(asd["MetricAlarms"])
            add_lines = []
            info["OK"] = 0
            info["ALARM"] = 0
            info["INSUFFICIENT_DATA"] = 0
            for alarm in asd["CompositeAlarms"]:
                info[alarm["StateValue"]] += 1
                if alarm["StateValue"] == "ALARM":
                    add_lines.append(
                        (
                            f"Composite: {alarm['AlarmName']}",
                            "dashboard_block_negative",
                            False,
                        )
                    )
            for alarm in asd["MetricAlarms"]:
                info[alarm["StateValue"]] += 1
                if alarm["StateValue"] == "ALARM":
                    add_lines.append(
                        (
                            f"MetricAlarm: {alarm['AlarmName']}",
                            "dashboard_block_negative",
                            False,
                        )
                    )
            if len(add_lines) > 0:
                add_lines.insert(
                    0, ("Alarms currently firing", "dashboard_block_label", True)
                )
            with self.mutex:
                self.additional_lines = add_lines
                self.alarm_data = asd
                self.info = info
                self.status = self.STATUS_READY
        else:
            with self.mutex:
                self.status = self.STATUS_ERROR
            return
