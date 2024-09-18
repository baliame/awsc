"""
Module for Secret Manager resources.
"""

import datetime
import json
from .base_control import Describer, ResourceLister, ResourceRefByClass, boolean_determiner_generator, format_timedelta


class SecretValueDescriber(Describer):
    """
    Describer control for AWS Secrets Manager secret values.
    """

    prefix = "asm_contents"
    title = "Secret Value"

    resource_type = "secret"
    main_provider = "secretsmanager"
    category = "Secrets Manager"
    subcategory = "Secret"
    describe_method = "get_secret_value"
    describe_kwarg_name = "SecretId"
    object_path = "."

    def pre_display_transform(self, data):
        """
        Allows transformation on the AWS response before committing it to text.
        """
        if 'SecretString' in data:
            data['SecretString'] = json.loads(data['SecretString'])
        return data


class SecretDescriber(Describer):
    """
    Describer control for AWS Secrets Manager secrets.
    """

    prefix = "asm_browser"
    title = "Secret"

    resource_type = "secret"
    main_provider = "secretsmanager"
    category = "Secrets Manager"
    subcategory = "Secret"
    describe_method = "describe_secret"
    describe_kwarg_name = "SecretId"
    object_path = "."


def _asm_determine_created(secret, **kwargs):
    """
    Column callback for extracting when a stack was created.
    """
    return format_timedelta(
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.datetime.fromisoformat(secret["CreatedDate"]), 1
    )

def _asm_determine_rotated(secret, **kwargs):
    """
    Column callback for extracting when a stack was created.
    """
    if "LastRotatedDate" in secret:
        return format_timedelta(
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.datetime.fromisoformat(secret["LastRotatedDate"]), 1
        )
    else:
        return "<never>"

class SecretResourceLister(ResourceLister):
    """
    Lister control for autoscaling launch configurations.
    """

    prefix = "asm_list"
    title = "Secrets"
    command_palette = ["secret", "secretmanager"]

    resource_type = "secret"
    main_provider = "secretsmanager"
    category = "Secrets Manager"
    subcategory = "Secrets"
    list_method = "list_secrets"
    item_path = ".SecretList"
    columns = {
        "name": {
            "path": ".Name",
            "size": 30,
            "weight": 0,
            "sort_weight": 0,
        },
        "created": {"path": _asm_determine_created, "size": 5, "weight": 1},
        "rotated": {"path": _asm_determine_rotated, "size": 5, "weight": 2},
        "autorotate": {"path": boolean_determiner_generator("RotationEnabled", True), "size": 5, "weight": 3},
    }
    describe_command = SecretDescriber.opener
    open_command = SecretValueDescriber.opener
    open_selection_arg = "entry"
    next_marker = "NextToken"
    next_marker_arg = "NextToken"
    primary_key = "name"
