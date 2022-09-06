"""
Module for EBS volumes.
"""
from .base_control import Describer, ResourceLister, tagged_column_generator


def _ebs_determine_size(entry):
    """
    Column callback for returning the size of an EBS volume in a nice format.
    """
    return f"{entry['Size']} GiB"


def _ebs_determine_attachment(self, entry):
    """
    Column callback for figuring out which instance an EBS volume is attached to.
    """
    for attachment in entry["Attachments"]:
        if attachment["State"] in ("attaching", "attached", "busy"):
            return attachment["InstanceId"]
    return ""


class EBSDescriber(Describer):
    """
    Describer control for EBS volumes.
    """

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


class EBSResourceLister(ResourceLister):
    """
    Lister control for EBS volumes.
    """

    prefix = "ebs_list"
    title = "EBS Volumes"
    command_palette = ["ebs"]

    resource_type = "ebs volume"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "EBS Volume"
    list_method = "describe_volumes"
    item_path = ".Volumes"
    columns = {
        "id": {"path": ".VolumeId", "size": 20, "weight": 0},
        **tagged_column_generator("name", "name", weight=1, sort_weight=0, size=30),
        "size": {"path": _ebs_determine_size, "size": 10, "weight": 2},
        "state": {"path": ".State", "size": 10, "weight": 3},
        "type": {"path": ".VolumeType", "size": 10, "weight": 4},
        "attached to": {"path": _ebs_determine_attachment, "size": 16, "weight": 5},
    }
    primary_key = "id"
    describe_command = EBSDescriber.opener
