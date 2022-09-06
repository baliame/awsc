"""
EC2 AMI resource controls.
"""
from .base_control import Describer, ResourceLister


class AMIDescriber(Describer):
    """
    Describer control for AMI resources.
    """

    prefix = "ami_browser"
    title = "Amazon Machine Image"

    def __init__(self, *args, entry_key="id", **kwargs):
        self.resource_key = "ec2"
        self.describe_method = "describe_images"
        self.describe_kwarg_name = "ImageIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".Images[0]"
        super().__init__(*args, entry_key=entry_key, **kwargs)


class AMIResourceLister(ResourceLister):
    """
    List control for AMI resources.

    Attributes
    ----------
    ec2 : awsc.termui.list_control.ListEntry
        List AMIs in the context of this EC2 instance.
    """

    prefix = "ami_list"
    title = "Amazon Machine Images"
    command_palette = ["ami", "image"]

    resource_type = "AMI"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "AMI"
    list_method = "describe_images"
    list_kwargs = {"Owners": ["self"]}
    item_path = ".Images"
    primary_key = "id"
    columns = {
        "id": {
            "path": ".ImageId",
            "size": 15,
            "weight": 0,
            "sort_weight": 0,
        },
        "name": {"path": ".Name", "size": 64, "weight": 1},
        "arch": {"path": ".Architecture", "size": 8, "weight": 2},
        "platform": {"path": ".PlatformDetails", "size": 10, "weight": 3},
        "type": {"path": ".ImageType", "size": 10, "weight": 4},
        "owner": {"path": ".ImageOwnerAlias", "size": 15, "weight": 5},
        "state": {"path": ".State", "size": 10, "weight": 6},
        "virt": {"path": ".VirtualizationType", "size": 10, "weight": 7},
    }

    describe_selection_arg = "entry"
    describe_command = AMIDescriber.opener

    def title_info(self):
        return None if self.ec2 is None else f"Instance: {self.ec2['instance id']}"

    def __init__(self, *args, ec2=None, **kwargs):
        self.ec2 = ec2
        if ec2 is not None:
            self.list_kwargs["ImageIds"] = [kwargs["ec2"]["image"]]
        super().__init__(*args, **kwargs)
