"""
Module for IAM policy resources.
"""

from .base_control import (
    Describer,
    ListResourceDocumentCreator,
    ResourceLister,
    SelectionAttribute,
    TemplateDict,
)
from .common import Common
from .resource_iam import EMPTY_POLICY_DOCUMENT
from .termui.ui import ControlCodes


class PolicyVersionDescriber(Describer):
    """
    Describer control for a policy version.
    """

    prefix = "policy_version_browser"
    title = "Policy Document"

    def title_info(self):
        return self.name

    def __init__(self, *args, policy="", **kwargs):
        self.resource_key = "iam"
        self.describe_method = "get_policy_version"
        self.object_path = ".PolicyVersion"
        self.arn = Common.Session.jq(".Arn").input(text=policy).first()
        self.name = Common.Session.jq(".PolicyName").input(text=policy).first()
        version = Common.Session.jq(".DefaultVersionId").input(text=policy).first()
        self.describe_kwargs = {"PolicyArn": self.arn, "VersionId": version}
        kwargs["entry"] = None
        kwargs["entry_key"] = None
        super().__init__(*args, **kwargs)


class PolicyDescriber(Describer):
    """
    Describer control for IAM policy resources.
    """

    prefix = "policy_browser"
    title = "Policy"

    def __init__(self, *args, entry_key="arn", **kwargs):
        self.resource_key = "iam"
        self.describe_method = "get_policy"
        self.describe_kwarg_name = "PolicyArn"
        self.object_path = ".Policy"
        self.additional_commands = {
            "d": {
                "command": PolicyVersionDescriber.opener,
                "data_arg": "policy",
                "tooltip": "View Policy Document",
                "kwargs": {"entry": None},
            }
        }
        super().__init__(*args, entry_key=entry_key, **kwargs)


@ResourceLister.Autocommand("UserLister", "m", "View policies", "user")
@ResourceLister.Autocommand("GroupLister", "m", "View policies", "group")
@ResourceLister.Autocommand("RoleLister", "m", "View policies", "role")
class PolicyLister(ResourceLister):
    """
    Lister control for IAM policy resources.
    """

    prefix = "policy_list"
    title = "Policies"
    command_palette = ["policy", "policies"]

    resource_type = "policy"
    main_provider = "iam"
    category = "IAM"
    subcategory = "Managed Policies"
    columns = {
        "name": {
            "path": ".PolicyName",
            "size": 25,
            "weight": 0,
            "sort_weight": 0,
        },
        "arn": {"path": ".PolicyArn", "size": 80, "weight": 1},
    }
    describe_command = PolicyDescriber.opener

    def title_info(self):
        if self.user is not None:
            return f"User: {self.user['name']}"
        if self.group is not None:
            return f"Group: {self.group['name']}"
        if self.role is not None:
            return f"Role: {self.role['name']}"
        return None

    def get_scope_tooltip(self):
        """
        Hotkey tooltip callback for policy scopes.
        """
        return f"Change Scope ({self.scope})"

    def change_scope(self, *args):
        """
        Hotkey callback for changing the viewed policy scopes.
        """
        idx = self.scopes.index(self.scope)
        newidx = idx + 1
        if newidx >= len(self.scopes):
            newidx = 0
        self.scope = self.scopes[newidx]
        self.list_kwargs["Scope"] = self.scope
        Common.Session.set_message("Refreshing...", Common.color("message_info"))
        self.refresh_data()

    def create_policy(self, *args):
        """
        Hotkey callback for creating a new policy.
        """
        creator = ListResourceDocumentCreator(
            "iam",
            "create_policy",
            None,
            as_json=["Tags"],
            initial_document={
                "PolicyName": "",
                "Path": "/",
                "Description": "",
                "Tags": [{"Key": "", "Value": ""}],
                **EMPTY_POLICY_DOCUMENT,
            },
        )
        creator.edit()
        self.refresh_data()

    def delete_policy(self, _):
        """
        Hotkey callback for deleting an existing policy. Additional validation is required for this one.
        """
        if "attached" not in self.selection or int(self.selection["attached"]) > 0:
            Common.Session.set_message(
                "Policy must be detached before deletion", Common.color("message_error")
            )
            return
        self.confirm_template(
            "delete_policy", TemplateDict({"PolicyArn": SelectionAttribute("arn")})
        )(self.selection)

    def detach_policy(self, _):
        """
        Hotkey callback for detaching the policy from the contextual IAM datatype.
        """
        if self.user is not None:
            dtype = "user"
            dname = self.user.name
        elif self.group is not None:
            dtype = "group"
            dname = self.group.name
        elif self.role is not None:
            dtype = "role"
            dname = self.role.name
        else:
            return
        argname = f"{dtype.capitalize()}Name"
        self.confirm_template(
            f"detach_{dtype}_policy",
            TemplateDict(
                {"PolicyArn": SelectionAttribute("arn"), argname: dname},
            ),
            action_name="Detach",
            from_what=dtype,
            from_what_name=dname,
        )(self.selection)

    def __init__(self, *args, user=None, group=None, role=None, **kwargs):
        isset = int(user is not None) + int(group is not None) + int(role is not None)
        if isset > 1:
            raise RuntimeError("Only one of user, group or role can be set.")
        self.user = user
        self.group = group
        self.role = role
        self.resource_key = "iam"
        self.scopes = ["All", "AWS", "Local"]
        self.scope = "All"
        if "selector_cb" in kwargs:
            self.primary_key = "arn"

        if user is not None:
            self.list_method = "list_attached_user_policies"
            self.list_kwargs = {"UserName": self.user["name"]}
            self.item_path = ".AttachedPolicies"
        elif group is not None:
            self.list_method = "list_attached_group_policies"
            self.list_kwargs = {"GroupName": self.group["name"]}
            self.item_path = ".AttachedPolicies"
        elif role is not None:
            self.list_method = "list_attached_role_policies"
            self.list_kwargs = {"RoleName": self.role["name"]}
            self.item_path = ".AttachedPolicies"
        else:
            self.list_method = "list_policies"
            self.list_kwargs = {"Scope": self.scope}
            self.item_path = ".Policies"
            self.columns["arn"]["path"] = ".Arn"
            self.columns["attached"] = {
                "path": ".AttachmentCount",
                "weight": 2,
                "size": 8,
            }

        super().__init__(*args, **kwargs)
        if isset == 0:
            self.add_hotkey("n", self.create_policy, "Create new policy")
            self.add_hotkey("s", self.change_scope, self.get_scope_tooltip)
            self.add_hotkey(ControlCodes.D, self.delete_policy, "Delete policy", True)
        else:
            self.add_hotkey(ControlCodes.D, self.detach_policy, "Detach policy", True)
