from .base_control import Describer, ResourceLister


class AMIResourceLister(ResourceLister):
    prefix = "ami_list"
    title = "Amazon Machine Images"
    command_palette = ["ami", "image"]

    def title_info(self):
        return self.title_info_data

    def __init__(self, *args, **kwargs):
        self.resource_key = "ec2"
        self.list_method = "describe_images"
        self.title_info_data = None
        self.list_kwargs = {"Owners": ["self"]}
        if "ec2" in kwargs:
            self.list_kwargs["ImageIds"] = [kwargs["ec2"]["image"]]
            self.title_info_data = "Instance: {0}".format(kwargs["ec2"]["instance id"])
        self.item_path = ".Images"
        self.column_paths = {
            "id": ".ImageId",
            "name": ".Name",
            "arch": ".Architecture",
            "platform": ".PlatformDetails",
            "type": ".ImageType",
            "owner": ".ImageOwnerAlias",
            "state": ".State",
            "virt": ".VirtualizationType",
        }
        self.imported_column_sizes = {
            "id": 15,
            "name": 64,
            "arch": 8,
            "platform": 10,
            "type": 10,
            "owner": 15,
            "state": 10,
            "virt": 10,
        }
        self.describe_command = AMIDescriber.opener
        self.imported_column_order = [
            "id",
            "name",
            "arch",
            "platform",
            "type",
            "owner",
            "state",
            "virt",
        ]
        self.primary_key = "id"
        self.sort_column = "id"
        super().__init__(*args, **kwargs)


class AMIDescriber(Describer):
    prefix = "ami_browser"
    title = "Amazon Machine Image"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="id", **kwargs
    ):
        self.resource_key = "ec2"
        self.describe_method = "describe_images"
        self.describe_kwarg_name = "ImageIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".Images[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
