"""
Module for IAM role resources.
"""

from .base_control import (
    Describer,
    ListResourceDocumentCreator,
    ResourceLister,
    SelectionAttribute,
    SelectorTemplateField,
    TemplateDict,
)
from .resource_iam import InlinePolicyAttacher
from .termui.ui import ControlCodes


class RoleDescriber(Describer):
    """
    Describer control for IAM Role resources.
    """

    prefix = "role_browser"
    title = "Role"

    def __init__(self, *args, **kwargs):
        self.resource_key = "iam"
        self.describe_method = "get_role"
        self.describe_kwarg_name = "RoleName"
        self.object_path = ".Role"
        super().__init__(*args, **kwargs)


@ResourceLister.Autocommand(
    "InstanceProfileLister", "u", "View roles", "instanceprofile"
)
class RoleLister(ResourceLister):
    """
    Lister control for IAM Role resources.
    """

    prefix = "role_list"
    title = "Roles"
    command_palette = ["role", "roles"]

    resource_type = "role"
    main_provider = "iam"
    category = "IAM"
    subcategory = "Role"
    columns = {
        "name": {
            "path": ".RoleName",
            "size": 25,
            "weight": 0,
            "sort_weight": 0,
        },
        "id": {"path": ".RoleId", "size": 15, "weight": 1},
        "path": {"path": ".Path", "size": 40, "weight": 2},
        "arn": {"path": ".Arn", "hidden": True},
    }
    describe_command = RoleDescriber.opener
    open_command = "m"

    def title_info(self):
        return (
            None
            if self.instanceprofile is None
            else f"InstanceProfile: {self.instanceprofile['name']}"
        )

    def create_role(self, _):
        """
        Hotkey callback for creating a new role.
        """
        creator = ListResourceDocumentCreator(
            "iam",
            "create_role",
            None,
            as_json=["Tags"],
            initial_document={
                "RoleName": "",
                "Path": "/",
                "PermissionsBoundary": "",
                "MaxSessionDuration": 3600,
                "AssumeRolePolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "",
                            "Effect": "Allow",
                            "Action": ["sts:AssumeRole"],
                            "Resource": "*",
                            "Condition": {},
                            "Principal": {},
                        }
                    ],
                },
                "Description": "",
                "Tags": [{"Key": "", "Value": ""}],
            },
        )
        creator.edit()
        self.refresh_data()

    @ResourceLister.Autohotkey("a", "Attach policy", True)
    def attach_policy(self, _):
        """
        Hotkey callback for attaching a policy to a role.
        """
        self.selector_template(
            "attach_role_policy",
            TemplateDict(
                {
                    "RoleName": SelectionAttribute("name"),
                    "PolicyArn": SelectorTemplateField(),
                }
            ),
            "Attach policy to role",
            "attach",
            "PolicyLister",
            resource_type="policy",
            success_template="Attaching policy {PolicyArn} to role {RoleName}",
        )(self.selection)

    def add_to_instance_profile(self, _):
        """
        Hotkey callback for adding the role to an instance profile.
        """
        self.selector_template(
            "add_role_to_instance_profile",
            TemplateDict(
                {
                    "RoleName": SelectionAttribute("name"),
                    "InstanceProfileName": SelectorTemplateField(),
                }
            ),
            "Add role to instance profile",
            "add",
            "InstanceProfileLister",
            resource_type="group",
            success_template="Adding role {RoleName} to instance profile {InstanceProfileName}",
        )(self.selection)

    def __init__(self, *args, instanceprofile=None, **kwargs):
        self.instanceprofile = instanceprofile
        self.list_method = (
            "list_roles" if self.instanceprofile is None else "get_instance_profile"
        )
        self.list_kwargs = (
            {}
            if self.instanceprofile is None
            else {"InstanceProfileName": self.instanceprofile["name"]}
        )
        self.item_path = (
            ".Roles" if self.instanceprofile is None else ".InstanceProfile.Roles"
        )

        super().__init__(*args, **kwargs)
        self.inliner = InlinePolicyAttacher(self, "role")
        if self.instanceprofile is None:
            self.add_hotkey("n", self.create_role, "Create Role")
            self.add_hotkey(
                "j", self.add_to_instance_profile, "Add to Instance Profile", True
            )
            self.confirm_template(
                "delete_role",
                TemplateDict(
                    {
                        "RoleName": SelectionAttribute("name"),
                    }
                ),
                hotkey=ControlCodes.D,
                hotkey_tooltip="Delete Role",
            )
        else:
            self.confirm_template(
                "remove_role_from_instance_profile",
                TemplateDict(
                    {
                        "RoleName": SelectionAttribute("name"),
                        "InstanceProfileName": self.instanceprofile["name"],
                    }
                ),
                success_template="Removing role {RoleName} from instance profile {InstanceProfileName}",
                action_name="Detach",
                from_what="instance profile",
                from_what_name=self.instanceprofile["name"],
                hotkey=ControlCodes.D,
                hotkey_tooltip="Detach from Instance Profile",
            )
