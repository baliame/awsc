"""
Module for EC2 instance class resources.
"""
from .base_control import Describer, ResourceLister


class InstanceClassDescriber(Describer):
    """
    Describer control for EC2 instance classes.
    """

    prefix = "instance_class_browser"
    title = "Instance Class"

    def __init__(self, *args, **kwargs):
        self.resource_key = "ec2"
        self.describe_method = "describe_instance_types"
        self.describe_kwarg_name = "InstanceTypes"
        self.describe_kwarg_is_list = True
        self.object_path = ".InstanceTypes[0]"
        super().__init__(*args, **kwargs)


class InstanceClassResourceLister(ResourceLister):
    """
    List control for EC2 instance classes.
    """

    prefix = "instance_class_list"
    title = "Instance Classes"
    command_palette = ["it", "instancetype", "instanceclass"]

    resource_type = "instance class"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "Instance Class"
    list_method = "describe_instance_types"
    item_path = ".InstanceTypes"
    list_kwargs = {"MaxResults": 20}
    columns = {
        "name": {
            "path": ".InstanceType",
            "size": 20,
            "weight": 0,
            "sort_weight": 0,
        },
        "cpus": {"path": ".VCpuInfo.DefaultVCpus", "size": 4, "weight": 1},
        "memory": {
            "path": lambda x: f"{x['MemoryInfo']['SizeInMiB']} MiB",
            "size": 10,
            "weight": 2,
        },
        "ebs optimization": {
            "path": ".EbsInfo.EbsOptimizedSupport",
            "size": 15,
            "weight": 3,
        },
        "network": {"path": ".NetworkInfo.NetworkPerformance", "size": 15, "weight": 4},
    }
    describe_command = InstanceClassDescriber.opener
