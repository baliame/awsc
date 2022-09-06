"""
Module for cloudwatch resources.
"""
import datetime

from .base_control import ResourceLister
from .common import BaseChart, Common


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
            "MetricDataQueries": (
                [
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
            ),
            "StartTime": (datetime.datetime.now() - datetime.timedelta(hours=24),),
            "EndTime": (datetime.datetime.now(),),
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
