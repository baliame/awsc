from .base_control import (
    DeleteResourceDialog,
    Describer,
    ListResourceDocumentCreator,
    ResourceLister,
    SingleRelationLister,
    SingleSelectorDialog,
)
from .common import Common
from .termui.alignment import CenterAnchor, Dimension
from .termui.dialog import DialogFieldCheckbox
from .termui.ui import ControlCodes


class SQSLister(ResourceLister):
    prefix = "sqs_list"
    title = "Queues"
    command_palette = ["sqs", "queue", "queues"]

    def delete_queue(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="queue",
            resource_identifier=self.selection["url"],
            callback=self.do_delete,
            action_name="Delete",
        )

    def do_delete(self, force, terminate_resources_field, **kwargs):
        if self.selection is None:
            return
        try:
            Common.Session.service_provider("sqs").delete_queue(
                QueueUrl=self.selection["url"],
            )
            Common.Session.set_message(
                "Deleting queue {0}".format(self.selection["url"]),
                Common.color("message_success"),
            )
        except Exception as e:
            Common.Session.set_message(str(e), Common.color("message_error"))
        self.refresh_data()

    def purge_queue(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="queue",
            resource_identifier=self.selection["url"],
            callback=self.do_purge,
            action_name="Purge",
        )

    def do_purge(self, force, terminate_resources_field, **kwargs):
        if self.selection is None:
            return
        try:
            Common.Session.service_provider("sqs").purge_queue(
                QueueUrl=self.selection["url"],
            )
            Common.Session.set_message(
                "Purging queue {0}".format(self.selection["url"]),
                Common.color("message_success"),
            )
        except Exception as e:
            Common.Session.set_message(str(e), Common.color("message_error"))
        self.refresh_data()

    def send_message(self, _):
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

    def create_queue(self, _):
        doc = {
            "QueueName": "",
            "Attributes": {
                "DelaySeconds": 0,
                "MaximumMessageSize": 262144,
                "MessageRetentionPeriod": 345600,
                "Policy": "",
                "ReceiveMessageWaitTimeSeconds": 0,
                "RedrivePolicy": "",
                "VisibilityTimeout": 30,
                "KmsMasterKeyId": "",
                "KmsDataKeyReusePeriodSeconds": 300,
                "SqsManagedSseEnabled": False,
                "FifoQueue": False,
                "ContentBasedDeduplication": False,
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

    def __init__(self, *args, **kwargs):
        self.resource_key = "sqs"
        self.list_method = "list_queues"
        self.item_path = ".QueueUrls"
        self.column_paths = {"url": ".", "available": self.determine_available_messages}
        self.imported_column_sizes = {
            "url": 80,
            "available": 9,
        }
        self.hidden_columns = {
            "arn": self.determine_queue_arn,
        }
        self.describe_command = SQSDescriber.opener

        self.imported_column_order = ["url", "available"]
        self.sort_column = "url"
        self.primary_key = "url"
        super().__init__(*args, **kwargs)
        self.add_hotkey(ControlCodes.D, self.delete_queue, "Delete Queue")
        self.add_hotkey(ControlCodes.P, self.purge_queue, "Purge Queue")
        self.add_hotkey(ControlCodes.S, self.send_message, "Send Message")
        self.add_hotkey(ControlCodes.N, self.create_queue, "Create Queue")

    def determine_queue_arn(self, v):
        attribs = Common.Session.service_provider("sqs").get_queue_attributes(
            QueueUrl=v, AttributeNames=["QueueArn"]
        )
        return attribs["Attributes"]["QueueArn"]

    def determine_available_messages(self, v):
        attribs = Common.Session.service_provider("sqs").get_queue_attributes(
            QueueUrl=v, AttributeNames=["ApproximateNumberOfMessages"]
        )
        return attribs["Attributes"]["ApproximateNumberOfMessages"]


class SQSDescriber(Describer):
    prefix = "sqs_browser"
    title = "Queue"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="url", **kwargs
    ):
        self.resource_key = "sqs"
        self.describe_method = "get_queue_attributes"
        self.describe_kwarg_name = "QueueUrl"
        self.describe_kwargs = {"AttributeNames": ["All"]}
        self.object_path = "."
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
