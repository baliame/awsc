"""
Definition snippets that may be used by other code.
"""
from copy import deepcopy

from .base_control import tag_finder_generator

MULTILISTER_DESCRIPTORS = {
    "ec2": {
        "resource_key": "ec2",
        "list_method": "describe_instances",
        "list_kwargs": {},
        "item_path": "[.Reservations[].Instances[]]",
        "column_paths": {
            "type": lambda x: "EC2 Instance",
            "id": ".InstanceId",
            "name": tag_finder_generator("Name"),
        },
        "hidden_columns": {},
    },
    "rds": {
        "resource_key": "rds",
        "list_method": "describe_db_instances",
        "list_kwargs": {},
        "item_path": ".DBInstances",
        "column_paths": {
            "type": lambda x: "RDS Instance",
            "id": ".DBInstanceIdentifier",
            "name": ".Endpoint.Address",
        },
        "hidden_columns": {},
    },
}
"""
Commonly used multilister descriptors.
"""


def multilister_with_compare_path(resource_key, compare_path, compare_as_list=False):
    """
    Convenience function for setting the compare path of a common multilister descriptor.

    Parameters
    ----------
    resource_key : str
        Key in MULTILISTER_DESCRIPTORS.
    compare_path : str
        The compare path to set.
    compare_as_list : bool
        The value to set for compare_as_list.

    Returns
    -------
    dict
        The appropriate key from MULTILISTER_DESCRIPTORS with compare_path set.
    """
    ret = deepcopy(MULTILISTER_DESCRIPTORS[resource_key])
    ret["compare_path"] = compare_path
    ret["compare_as_list"] = compare_as_list
    return ret
