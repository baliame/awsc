"""
Module for IAM group resources.
"""

from .base_control import (
    Describer,
    ResourceLister,
    SelectionAttribute,
    SelectorTemplateField,
    SingleNameDialog,
    TemplateDict,
)
from .common import Common
from .resource_iam import InlinePolicyAttacher
from .termui.common import Commons
from .termui.ui import ControlCodes


class GroupDescriber(Describer):
    """
    Describer control for IAM groups.
    """

    prefix = "group_browser"
    title = "Group"

    def __init__(self, *args, **kwargs):
        self.resource_key = "iam"
        self.describe_method = "get_group"
        self.describe_kwarg_name = "GroupName"
        self.object_path = ".Group"
        super().__init__(*args, **kwargs)


@ResourceLister.Autocommand("UserLister", "g", "List groups for user", "user")
class GroupLister(ResourceLister):
    """
    Lister control for IAM groups.
    """

    prefix = "group_list"
    title = "Groups"
    command_palette = ["group", "groups"]

    resource_type = "group"
    main_provider = "iam"
    category = "IAM"
    subcategory = "Group"
    item_path = ".Groups"
    columns = {
        "name": {
            "path": ".GroupName",
            "size": 25,
            "weight": 0,
            "sort_weight": 0,
        },
        "id": {"path": ".GroupId", "size": 15, "weight": 1},
        "path": {"path": ".Path", "size": 40, "weight": 2},
        "arn": {"path": ".Arn", "hidden": True},
    }
    describe_command = GroupDescriber.opener
    open_command = "m"

    def title_info(self):
        return f"User: {self.user['name']}" if self.user is not None else None

    @ResourceLister.Autohotkey("a", "Attach policy", True)
    def attach_policy(self, _):
        """
        Hotkey callback for attaching a policy to a group.
        """
        self.selector_template(
            "attach_group_policy",
            TemplateDict(
                {
                    "GroupName": SelectionAttribute("name"),
                    "PolicyArn": SelectorTemplateField(),
                }
            ),
            "Attach policy to group",
            "attach",
            "PolicyLister",
            resource_type="policy",
            success_template="Attaching policy {PolicyArn} to group {GroupName}",
        )(self.selection)

    def create_group(self, _):
        """
        Hotkey callback for creating a new group.
        """
        SingleNameDialog(
            self.parent,
            "Create new group",
            self.do_create,
            label="Name:",
            what="name",
            subject="group",
            default="",
            caller=self,
            accepted_inputs=Commons.alphanum_with_symbols("+=,.@_-"),
        )

    def do_create(self, name):
        """
        Action callback for creating a new group.
        """
        Common.generic_api_call(
            "iam",
            "create_group",
            {"GroupName": name},
            "Create Group",
            "IAM",
            subcategory="Group",
            success_template="Creating group {GroupName}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def do_remove(self, **kwargs):
        """
        Action callback for removing a user from a group.
        """
        Common.generic_api_call(
            "iam",
            "remove_user_from_group",
            {"GroupName": self.selection["name"], "UserName": self.user["name"]},
            "Remove User From Group",
            "IAM",
            subcategory="Group",
            success_template="Removing user {UserName} from group {GroupName}",
            resource=self.user["name"],
        )
        self.refresh_data()

    def add_user_to_group(self, _):
        """
        Hotkey callback for adding a user to a group.
        """
        self.selector_template(
            "add_user_to_group",
            TemplateDict(
                {
                    "GroupName": SelectionAttribute("name"),
                    "UserName": SelectorTemplateField(),
                }
            ),
            "Add user to group",
            "add",
            "UserLister",
            resource_type="user",
            success_template="Adding user {UserName} to group {GroupName}",
        )(self.selection)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        self.list_method = "list_groups_for_user" if user is not None else "list_groups"
        self.item_path = ".Groups"
        self.list_kwargs = {"UserName": self.user["name"]} if user is not None else {}

        super().__init__(*args, **kwargs)
        self.inliner = InlinePolicyAttacher(self, "group")
        if self.user is None:
            self.confirm_template(
                "delete_group",
                TemplateDict(
                    {
                        "GroupName": SelectionAttribute("name"),
                    }
                ),
                hotkey=ControlCodes.D,
                hotkey_tooltip="Delete Group",
            )
            self.add_hotkey("j", self.add_user_to_group, "Add User", True)
            self.add_hotkey("n", self.create_group, "Create Group")
        else:
            self.confirm_template(
                "remove_user_from_group",
                TemplateDict(
                    {
                        "UserName": self.user["name"],
                        "GroupName": SelectionAttribute("name"),
                    }
                ),
                resource_type="user",
                resource_identifier=self.user["name"],
                from_what="group",
                from_what_name=SelectionAttribute("name"),
                action_name="Remove",
                hotkey=ControlCodes.D,
                hotkey_tooltip="Remove from Group",
            )
