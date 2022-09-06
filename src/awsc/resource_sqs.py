"""
Module for SQS resources.
"""
from typing import Dict

from .base_control import (
    Describer,
    ListResourceDocumentCreator,
    ResourceLister,
    SelectionAttribute,
    TemplateDict,
)
from .common import Common
from .termui.ui import ControlCodes


def _sqs_determine_queue_arn(result):
    return SQSLister.get_attrib_cache(result, "QueueArn")


def _sqs_determine_available_messages(result):
    return SQSLister.get_attrib_cache(result, "ApproximateNumberOfMessages")


class SQSDescriber(Describer):
    """
    Describer control for SQS queues.
    """

    prefix = "sqs_browser"
    title = "Queue"

    def __init__(self, *args, entry_key="url", **kwargs):
        self.resource_key = "sqs"
        self.describe_method = "get_queue_attributes"
        self.describe_kwarg_name = "QueueUrl"
        self.describe_kwargs = {"AttributeNames": ["All"]}
        self.object_path = "."
        super().__init__(*args, entry_key=entry_key, **kwargs)


class SQSLister(ResourceLister):
    """
    Lister control for SQS queues.
    """

    _sqs_attrib_cache: Dict[str, str] = {}

    prefix = "sqs_list"
    title = "Queues"
    command_palette = ["sqs", "queue", "queues"]

    resource_type = "Queue"
    main_provider = "sqs"
    category = "SQS"
    subcategory = "Queue"
    list_method = "list_queues"
    item_path = ".QueueUrls"
    columns = {
        "url": {
            "path": ".",
            "size": 80,
            "weight": 0,
            "sort_weight": 0,
        },
        "available": {
            "path": _sqs_determine_available_messages,
            "size": 9,
            "weight": 1,
        },
        "name": {"path": ".", "hidden": True},
        "arn": {"path": _sqs_determine_queue_arn, "hidden": True},
    }
    describe_command = SQSDescriber.opener
    primary_key = "url"

    @ResourceLister.Autohotkey("s", "Send message", True)
    def send_message(self, _):
        """
        Hotkey callback for inserting a message into the queue.
        """
        if self.selection is None:
            return
        doc = {
            "MessageBody": "",
            "DelaySeconds": 0,
            "MessageAttributes": {},
            "MessageSystemAttributes": {},
        }
        if self.selection["arn"].endswith(".fifo"):
            doc["MessageDeduplicationId"]: ""
            doc["MessageGroupId"]: ""
        creator = ListResourceDocumentCreator(
            "sqs",
            "send_message",
            None,
            as_json=["MessageAttributes", "MessageSystemAttributes"],
            initial_document=doc,
            static_fields={"QueueUrl": self.selection["url"]},
            message="Message successfully sent",
        )
        creator.edit()

    @ResourceLister.Autohotkey("n", "Create queue")
    def create_queue(self, _):
        """
        Hotkey callback for creating a new queue.
        """
        doc = {
            "QueueName": "",
            "Attributes": {
                "DelaySeconds": "0",
                "MaximumMessageSize": "262144",
                "MessageRetentionPeriod": "345600",
                "Policy": "",
                "ReceiveMessageWaitTimeSeconds": "0",
                "RedrivePolicy": "",
                "VisibilityTimeout": "30",
                "KmsMasterKeyId": "",
                "KmsDataKeyReusePeriodSeconds": "300",
                "SqsManagedSseEnabled": "false",
                "FifoQueue": "false",
                "ContentBasedDeduplication": "false",
                "DeduplicationScope": "queue",
                "FifoThroughputLimit": "perQueue",
            },
            "tags": {},
        }
        creator = ListResourceDocumentCreator(
            "sqs",
            "create_queue",
            None,
            as_json=["Attributes", "tags"],
            initial_document=doc,
        )
        creator.edit()

    @ResourceLister.Autohotkey(ControlCodes.P, "Purge Queue", True)
    def purge(self, _):
        """
        Hotkey callback for purging a queue.
        """
        self.confirm_template(
            "purge_queue",
            TemplateDict(
                {
                    "QueueUrl": SelectionAttribute("url"),
                }
            ),
            action_name="Purge",
        )(self.selection)

    @ResourceLister.Autohotkey(ControlCodes.D, "Delete Queue", True)
    def delete_queue(self, _):
        """
        Hotkey callback for queue deletion.
        """
        self.confirm_template(
            "delete_queue",
            TemplateDict(
                {
                    "QueueUrl": SelectionAttribute("url"),
                }
            ),
        )(self.selection)

    def refresh_data(self, *args, **kwargs):
        SQSLister._attrib_cache = {}
        return super().refresh_data(*args, **kwargs)

    @classmethod
    def get_attrib_cache(cls, url, attrib):
        """
        Returns a queue attribute from the attribute cache.

        Parameters
        ----------
        url : str
            The url of the queue for which an attribute is being queried.
        attrib : str
            The name of the attribute to query.

        Returns
        -------
        str
            The queue attribute, or n/a if it does not exist.
        """
        if url not in cls._attrib_cache:
            resps = Common.generic_api_call(
                "sqs",
                "get_queue_attributes",
                {"QueueUrl": url, "AttributeNames": ["All"]},
                "Get Queue Attributes",
                "SQS",
                subcategory="Queue",
                resource=url,
            )
            if resps["Success"]:
                attribs = resps["Response"]
                cls._attrib_cache[url] = attribs
        try:
            return cls._attrib_cache[url]["Attributes"][attrib]
        except KeyError:
            return "<n/a>"
