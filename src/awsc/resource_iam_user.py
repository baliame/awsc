"""
Module for IAM user resources.
"""

from .base_control import (
    DeleteResourceDialog,
    Describer,
    ListResourceDocumentCreator,
    ResourceLister,
    SelectionAttribute,
    SelectorTemplateField,
    SingleNameDialog,
    TemplateDict,
)
from .common import Common
from .resource_iam import InlinePolicyAttacher
from .termui.ui import ControlCodes


class UserDescriber(Describer):
    """
    Describer control for user resources.
    """

    prefix = "user_browser"
    title = "User"

    def __init__(self, *args, **kwargs):
        self.resource_key = "iam"
        self.describe_method = "get_user"
        self.describe_kwarg_name = "UserName"
        self.object_path = ".User"
        super().__init__(*args, **kwargs)


@ResourceLister.Autocommand("GroupLister", "u", "List group users", "group")
class UserLister(ResourceLister):
    """
    Lister control for user resources.
    """

    prefix = "user_list"
    title = "Users"
    command_palette = ["user", "users"]

    resource_type = "user"
    main_provider = "iam"
    category = "IAM"
    subcategory = "User"
    item_path = ".Users"
    columns = {
        "name": {
            "path": ".UserName",
            "size": 25,
            "weight": 0,
            "sort_weight": 0,
        },
        "path": {"path": ".Path", "size": 40, "weight": 1},
        "last login": {"path": ".PasswordLastUsed", "size": 15, "weight": 2},
        "arn": {"path": ".Arn", "hidden": True},
    }
    describe_command = UserDescriber.opener
    open_command = "m"

    def title_info(self):
        return f"Group: {self.group['name']}" if self.group is not None else None

    def create_user(self, _):
        """
        Hotkey callback for creating a new user.
        """
        creator = ListResourceDocumentCreator(
            "iam",
            "create_user",
            None,
            as_json=["Tags"],
            initial_document={
                "UserName": "",
                "Path": "/",
                "PermissionsBoundary": "",
                "Tags": [{"Key": "", "Value": ""}],
            },
        )
        creator.edit()
        self.refresh_data()

    def delete_user(self, _):
        """
        Hotkey callback for deleting a user.
        """
        self.confirm_template(
            "delete_user",
            TemplateDict(
                {
                    "UserName": SelectionAttribute("name"),
                }
            ),
        )(self.selection)

    @ResourceLister.Autohotkey("a", "Attach Policy", True)
    def attach_policy(self, _):
        """
        Hotkey callback for attaching a policy to a user.
        """
        self.selector_template(
            "attach_user_policy",
            TemplateDict(
                {
                    "UserName": SelectionAttribute("name"),
                    "PolicyArn": SelectorTemplateField(),
                }
            ),
            "Attach policy to user",
            "attach",
            "PolicyLister",
            resource_type="policy",
            success_template="Attaching policy {PolicyArn} to user {UserName}",
        )(self.selection)

    def add_user_to_group(self, _):
        """
        Hotkey callback for adding a user to a group.
        """
        self.selector_template(
            "add_user_to_group",
            TemplateDict(
                {
                    "UserName": SelectionAttribute("name"),
                    "GroupName": SelectorTemplateField(),
                }
            ),
            "Add user to group",
            "add",
            "GroupLister",
            resource_type="group",
            success_template="Adding user {UserName} to group {GroupName}",
        )(self.selection)

    def remove_from_group(self, _):
        """
        Hotkey callback for removing a user from a group.
        """
        self.confirm_template(
            "remove_user_from_group",
            TemplateDict(
                {
                    "UserName": SelectionAttribute("name"),
                    "GroupName": self.group["name"],
                }
            ),
            from_what="group",
            from_what_name=self.group["name"],
            action_name="Remove",
        )(self.selection)

    def determine_login_profile(self, user):
        """
        Check if a user has a login profile.

        Parameters
        ----------
        user : str
            The username to check.

        Returns
        -------
        bool
            True if the user has a login profile.
        """
        resp = Common.generic_api_call(
            "iam",
            "get_login_profile",
            {"UserName": user},
            "Get Login Profile",
            "IAM",
            subcategory="User",
            resource=user,
        )
        if resp["Success"]:
            return True
        return False

    @ResourceLister.Autohotkey("p", "Get/create login profile", True)
    def get_or_create_login_profile(self, _):
        """
        Hotkey callback for retrieving the user login profile. If one doesn't exist, a dialog is presented to create one.
        """
        has_login_profile = self.determine_login_profile(self.selection["name"])
        if has_login_profile:
            Common.Session.push_frame(
                LoginProfileDescriber.opener(
                    entry=self.selection, caller=self, pushed=True
                )
            )
        else:
            SingleNameDialog(
                self.parent,
                f"Create login profile for {self.selection['name']}",
                self.do_create_login_profile,
                label="Password:",
                what="password",
                subject="login profile",
                default="",
                caller=self,
            )

    def do_create_login_profile(self, password):
        """
        Action callback for the login profile creation dialog.

        Parameters
        ----------
        password : str
            Password for the new login profile.
        """
        resp = Common.generic_api_call(
            "iam",
            "create_login_profile",
            {
                "UserName": self.selection["name"],
                "Password": password,
                "PasswordResetRequired": True,
            },
            "Create Login Profile",
            "IAM",
            subcategory="User",
            resource=self.selection["name"],
        )
        if resp["Success"]:
            Common.Session.push_frame(
                LoginProfileDescriber.opener(
                    entry=self.selection, caller=self, pushed=True
                )
            )

    def __init__(self, *args, group=None, **kwargs):
        self.group = group
        self.list_method = "list_users" if group is None else "get_group"
        self.list_kwargs = {"GroupName": group["name"]} if group is not None else {}
        super().__init__(*args, **kwargs)
        self.inliner = InlinePolicyAttacher(self, "user")
        self.add_hotkey("a", self.attach_policy, "Attach Policy", True)
        if self.group is None:
            self.add_hotkey("j", self.add_user_to_group, "Add to Group", True)
            self.add_hotkey(ControlCodes.D, self.delete_user, "Delete User", True)
            self.add_hotkey("n", self.create_user, "Create User")
        else:
            self.add_hotkey(
                ControlCodes.D, self.remove_from_group, "Remove from Group", True
            )


class LoginProfileDescriber(Describer):
    """
    Describer control for login profiles.
    """

    prefix = "login_profile_browser"
    title = "Login Profile"

    def title_info(self):
        return f"User: {self.user['name']}"

    def __init__(self, *args, entry, **kwargs):
        self.user = entry
        self.resource_key = "iam"
        self.describe_method = "get_login_profile"
        self.describe_kwarg_name = "UserName"
        self.object_path = ".LoginProfile"
        super().__init__(*args, entry=entry, **kwargs)
        self.add_hotkey(
            ControlCodes.D, self.delete_login_profile, "Delete Login Profile"
        )

    # TODO: Create implementation of confirm_template for Describers.
    @Describer.Autohotkey(ControlCodes.D, "Delete login profile")
    def delete_login_profile(self, _):
        """
        Hotkey callback for deleting a login profile.
        """
        DeleteResourceDialog.opener(
            caller=self,
            resource_type="login profile",
            resource_identifier=self.user["name"],
            from_what="user",
            from_what_name=self.user["name"],
            callback=self.do_delete_login_profile,
        )

    def do_delete_login_profile(self, *args, **kwargs):
        """
        Action callback for deleting a login profile.
        """
        resp = Common.generic_api_call(
            "iam",
            "delete_login_profile",
            {
                "UserName": self.user["name"],
            },
            "Delete Login Profile",
            "IAM",
            subcategory="User",
            resource=self.user["name"],
            success_template="Deleting login profile for {UserName}",
        )
        if resp["Success"]:
            Common.Session.pop_frame()
