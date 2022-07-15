from .base_control import Describer, ResourceLister


class InstanceClassResourceLister(ResourceLister):
    prefix = "instance_class_list"
    title = "Instance Classes"
    command_palette = ["it", "instancetype", "instanceclass"]

    def __init__(self, *args, **kwargs):
        self.resource_key = "ec2"
        self.list_method = "describe_instance_types"
        self.item_path = ".InstanceTypes"
        self.list_kwargs = {"MaxResults": 20}
        self.column_paths = {
            "name": ".InstanceType",
            "cpus": ".VCpuInfo.DefaultVCpus",
            "memory": lambda x: "{0} MiB".format(x["MemoryInfo"]["SizeInMiB"]),
            "ebs optimization": ".EbsInfo.EbsOptimizedSupport",
            "network": ".NetworkInfo.NetworkPerformance",
        }
        self.imported_column_sizes = {
            "name": 20,
            "cpus": 4,
            "memory": 10,
            "ebs optimization": 15,
            "network": 15,
        }
        self.next_marker = "NextToken"
        self.next_marker_arg = "NextToken"
        self.imported_column_order = [
            "name",
            "cpus",
            "memory",
            "ebs optimization",
            "network",
        ]
        self.sort_column = "name"
        self.primary_key = "name"
        self.describe_command = InstanceClassDescriber.opener
        super().__init__(*args, **kwargs)


class InstanceClassDescriber(Describer):
    prefix = "instance_class_browser"
    title = "Instance Class"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "ec2"
        self.describe_method = "describe_instance_types"
        self.describe_kwarg_name = "InstanceTypes"
        self.describe_kwarg_is_list = True
        self.object_path = ".InstanceTypes[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
