"""
Module for IAM instance profile related resources.
"""

from .base_control import (
    Describer,
    ResourceLister,
    SelectionAttribute,
    SelectorTemplateField,
    TemplateDict,
)
from .termui.ui import ControlCodes


class InstanceProfileDescriber(Describer):
    """
    Describer control for IAM instance Profiles.
    """

    prefix = "instance_profile_browser"
    title = "Instance Profile"

    def __init__(self, *args, entry, entry_key="name", **kwargs):
        from .arn import ARN

        self.resource_key = "iam"
        self.describe_method = "get_instance_profile"
        self.describe_kwarg_name = "InstanceProfileName"
        self.object_path = ".InstanceProfile"
        if entry_key == "id":  # id is an Arn from a single relation lister
            arn = ARN(entry["id"])
            entry_key = "name"
            entry["name"] = arn.resource_id_first
        super().__init__(*args, entry=entry, entry_key=entry_key, **kwargs)


def _instance_profile_determine_role_count(instanceprofile):
    return str(len(instanceprofile["Roles"])) if "Roles" in instanceprofile else 0


@ResourceLister.Autocommand("RoleLister", "u", "View instance profile", "role")
class InstanceProfileLister(ResourceLister):
    """
    Lister control for IAM Instance Profiles.
    """

    prefix = "instance_profile_list"
    title = "Instance Profiles"
    command_palette = ["instanceprofile", "instanceprofiles"]

    resource_type = "instance profile"
    main_provider = "iam"
    category = "IAM"
    subcategory = "Instance Profile"
    item_path = ".InstanceProfiles"
    columns = {
        "name": {
            "path": ".InstanceProfileName",
            "size": 25,
            "weight": 0,
            "sort_weight": 0,
        },
        "id": {"path": ".InstanceProfileId", "size": 15, "weight": 1},
        "path": {"path": ".Path", "size": 40, "weight": 2},
        "roles": {
            "path": _instance_profile_determine_role_count,
            "size": 5,
            "weight": 3,
        },
        "arn": {"path": ".Arn", "hidden": True},
    }
    describe_command = InstanceProfileDescriber.opener
    open_command = "u"

    def title_info(self):
        return None if self.role is None else f"Role: {self.role['name']}"

    def add_role(self, _):
        """
        Hotkey callback for adding a role to an instance profiel.
        """
        self.selector_template(
            "add_role_to_instance_profile",
            TemplateDict(
                {
                    "InstanceProfileName": SelectionAttribute("name"),
                    "RoleName": SelectorTemplateField(),
                }
            ),
            "Add role to instance profile",
            "add",
            "RoleLister",
            resource_type="group",
            success_template="Adding role {RoleName} to instance profile {InstanceProfileName}",
        )(self.selection)

    def __init__(self, *args, role=None, **kwargs):
        self.role = role
        self.list_method = (
            "list_instance_profiles"
            if self.role is None
            else "list_instance_profiles_for_role"
        )
        self.list_kwargs = {} if self.role is None else {"RoleName": self.role["name"]}
        super().__init__(*args, **kwargs)
        if self.role is None:
            self.add_hotkey("j", self.add_role, "Attach Role", True)
            self.confirm_template(
                "delete_instance_profile",
                TemplateDict(
                    {
                        "InstanceProfileName": SelectionAttribute("name"),
                    }
                ),
                hotkey=ControlCodes.D,
                hotkey_tooltip="Delete Instance Profile",
            )
        else:
            self.confirm_template(
                "remove_role_from_instance_profile",
                TemplateDict(
                    {
                        "RoleName": self.role["name"],
                        "InstanceProfileName": SelectionAttribute("name"),
                    }
                ),
                success_template="Removing role {RoleName} from instance profile {InstanceProfileName}",
                action_name="Detach",
                resource_type="role",
                resource_identifier=self.role["name"],
                from_what="instance profile",
                from_what_name=SelectionAttribute("name"),
                hotkey=ControlCodes.D,
                hotkey_tooltip="Detach Instance Profile",
            )
