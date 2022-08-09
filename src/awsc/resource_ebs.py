from .base_control import Describer, ResourceLister


class EBSResourceLister(ResourceLister):
    prefix = "ebs_list"
    title = "EBS Volumes"
    command_palette = ["ebs"]

    def __init__(self, *args, **kwargs):
        self.resource_key = "ec2"
        self.list_method = "describe_volumes"
        self.item_path = ".Volumes"
        self.column_paths = {
            "id": ".VolumeId",
            "name": self.tag_finder_generator("Name"),
            "size": self.determine_size,
            "state": ".State",
            "type": ".VolumeType",
            "attached to": self.determine_attachment,
        }
        self.imported_column_sizes = {
            "id": 20,
            "name": 32,
            "size": 10,
            "state": 10,
            "type": 10,
            "attached to": 16,
        }
        self.imported_column_order = [
            "id",
            "name",
            "size",
            "state",
            "type",
            "attached to",
        ]
        self.list_kwargs = {}
        self.primary_key = "id"
        self.sort_column = "id"
        self.describe_command = EBSDescriber.opener
        super().__init__(*args, **kwargs)

    def determine_size(self, entry):
        return f"{entry['Size']} GiB"

    def determine_attachment(self, entry):
        for attachment in entry["Attachments"]:
            if attachment["State"] in ("attaching", "attached", "busy"):
                return attachment["InstanceId"]
        return ""


class EBSDescriber(Describer):
    prefix = "ebs_browser"
    title = "EBS Volume"

    def __init__(self, *args, entry_key="id", **kwargs):
        self.resource_key = "ec2"
        self.describe_method = "describe_volumes"
        self.describe_kwarg_name = "VolumeIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".Volumes[0]"
        super().__init__(
            *args,
            entry_key=entry_key,
            **kwargs,
        )
