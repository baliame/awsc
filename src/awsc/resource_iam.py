from botocore import exceptions as botoerror

from .base_control import (
    DeleteResourceDialog,
    Describer,
    ListResourceDocumentCreator,
    ResourceLister,
    SingleNameDialog,
    SingleSelectorDialog,
)
from .common import Common
from .termui.alignment import CenterAnchor, Dimension
from .termui.common import Commons
from .termui.ui import ControlCodes


class InlinePolicyAttacher:
    def __init__(self, parent, datatype):
        self.datatype = datatype
        self.parent = parent
        self.client = Common.Session.service_provider("iam")

        self.get = getattr(self.client, "get_{0}_policy".format(datatype))
        self.put_method = "put_{0}_policy".format(datatype)
        self.arg = "{0}Name".format(datatype.capitalize())

    def attach_inline_policy(self, _):
        if self.parent.selection is None:
            return
        SingleNameDialog(
            self.parent.parent,
            "Attach new or edit existing inline policy for {0}".format(self.datatype),
            self.do_attach_inline,
            label="Policy name:",
            what="name",
            subject="policy",
            default="",
            caller=self.parent,
            accepted_inputs=Commons.alphanum_with_symbols("+=,.@_-"),
        )

    def do_attach_inline(self, name, selection_is_policy=False):
        if self.parent.selection is None:
            return
        if selection_is_policy:
            kwargs = {"PolicyName": self.parent.selection["name"], self.arg: name}
        else:
            kwargs = {self.arg: self.parent.selection["name"], "PolicyName": name}
        try:
            chk = self.get(**kwargs)
            initial_document = {"PolicyDocument": chk["PolicyDocument"]}
        except self.client.exceptions.NoSuchEntityException:
            initial_document = {
                "PolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "",
                            "Effect": "Deny",
                            "Action": [""],
                            "Resource": "*",
                            "Condition": {},
                        }
                    ],
                }
            }
        except botoerror.ClientError as e:
            Common.clienterror(
                e,
                "Retrieve Inline {0} Policy".format(self.datatype.capitalize()),
                "IAM",
                set_message=True,
            )
            return
        except Exception as e:
            Common.error(
                str(e),
                "Retrieve Inline {0} Policy".format(self.datatype.capitalize()),
                "IAM",
                set_message=True,
            )
            return

        creator = ListResourceDocumentCreator(
            "iam",
            self.put_method,
            None,
            initial_document,
            as_json=False,
            static_fields=kwargs,
            message="Put policy successful",
        )
        creator.edit()
        self.parent.refresh_data()


class UserLister(ResourceLister):
    prefix = "user_list"
    title = "Users"
    command_palette = ["user", "users"]

    def title_info(self):
        return (
            "Group: {0}".format(self.group["name"]) if self.group is not None else None
        )

    def create_user(self, _):
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
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="user",
            resource_identifier=self.selection["name"],
            callback=self.do_delete,
            action_name="Delete",
        )

    def do_delete(self, **kwargs):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "delete_user",
            {
                "UserName": self.selection["name"],
            },
            "Delete User",
            "IAM",
            subcategory="User",
            success_template="Deleting user {UserName}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def do_attach(self, policy_arn):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "attach_user_policy",
            {
                "UserName": self.selection["name"],
                "PolicyArn": policy_arn,
            },
            "Attach Managed User Policy",
            "IAM",
            subcategory="User",
            success_template="Attaching policy {PolicyArn} to user {UserName}",
            resource=self.selection["name"],
        )

    def attach_policy(self, _):
        if self.selection is None:
            return
        SingleSelectorDialog(
            self.parent,
            "Attach policy to user",
            "policy",
            "attach",
            PolicyLister,
            self.do_attach,
            caller=self,
        )

    def add_user_to_group(self, _):
        if self.selection is None:
            return
        SingleSelectorDialog(
            self.parent,
            "Add user to group",
            "group",
            "add",
            GroupLister,
            self.do_add_to_group,
            caller=self,
        )

    def do_add_to_group(self, group):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "add_user_to_group",
            {"UserName": self.selection["name"], "GroupName": group},
            "Add User to Group",
            "IAM",
            subcategory="User",
            success_template="Adding user {UserName} to group {GroupName}",
            resource=self.selection["name"],
        )

    def remove_from_group(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="user",
            resource_identifier=self.selection["name"],
            from_what="group",
            from_what_name=self.group["name"],
            callback=self.do_remove,
            action_name="Remove",
        )

    def do_remove(self, **kwargs):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "remove_user_from_group",
            {"UserName": self.selection["name"], "GroupName": self.group["name"]},
            "Remove User from Group",
            "IAM",
            subcategory="User",
            success_template="Removing user {UserName} from group {GroupName}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def determine_login_profile(self, user):
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

    def get_or_create_login_profile(self, _):
        if self.selection is None:
            return
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
                "Create login profile for {0}".format(self.selection["name"]),
                self.do_create_login_profile,
                label="Password:",
                what="password",
                subject="login profile",
                default="",
                caller=self,
            )

    def do_create_login_profile(self, password):
        if self.selection is None:
            return
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
        self.resource_key = "iam"
        self.group = group
        self.list_method = "list_users" if group is None else "get_group"
        self.list_kwargs = {"GroupName": group["name"]} if group is not None else {}
        self.item_path = ".Users"
        self.column_paths = {
            "name": ".UserName",
            "path": ".Path",
            "last login": ".PasswordLastUsed",
        }
        self.imported_column_sizes = {
            "name": 25,
            "path": 40,
            "last login": 15,
        }
        self.hidden_columns = {
            "arn": ".Arn",
        }
        self.describe_command = UserDescriber.opener
        self.open_command = "m"
        self.open_selection_arg = "user"
        self.additional_commands = {
            "m": {
                "command": PolicyLister.opener,
                "selection_arg": "user",
                "tooltip": "View Managed Policies",
            },
            "g": {
                "command": GroupLister.opener,
                "selection_arg": "user",
                "tooltip": "List Groups for User",
            },
            "p": {
                "command": InlinePolicyLister.opener,
                "selection_arg": "data",
                "tooltip": "View Inline Policies",
                "kwargs": {
                    "datatype": "user",
                },
            },
        }

        self.imported_column_order = ["name", "path", "last login"]
        self.sort_column = "name"
        super().__init__(*args, **kwargs)
        self.inliner = InlinePolicyAttacher(self, "user")
        self.add_hotkey("a", self.attach_policy, "Attach Policy")
        self.add_hotkey("c", self.create_user, "Create User")
        self.add_hotkey("i", self.inliner.attach_inline_policy, "Put Inline Policy")
        self.add_hotkey(
            "p", self.get_or_create_login_profile, "Get/Create Login Profile"
        )
        if self.group is None:
            self.add_hotkey("j", self.add_user_to_group, "Add to Group")
            self.add_hotkey(ControlCodes.D, self.delete_user, "Delete User")
        else:
            self.add_hotkey(ControlCodes.D, self.remove_from_group, "Remove from Group")


class UserDescriber(Describer):
    prefix = "user_browser"
    title = "User"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "iam"
        self.describe_method = "get_user"
        self.describe_kwarg_name = "UserName"
        self.object_path = ".User"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class LoginProfileDescriber(Describer):
    prefix = "login_profile_browser"
    title = "Login Profile"

    def title_info(self):
        return "User: {0}".format(self.user["name"])

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.user = entry
        self.resource_key = "iam"
        self.describe_method = "get_login_profile"
        self.describe_kwarg_name = "UserName"
        self.object_path = ".LoginProfile"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
        self.add_hotkey(
            ControlCodes.D, self.delete_login_profile, "Delete Login Profile"
        )

    def delete_login_profile(self, _):
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="login profile",
            resource_identifier=self.user["name"],
            from_what="user",
            from_what_name=self.user["name"],
            callback=self.do_delete_login_profile,
            action_name="Delete",
        )

    def do_delete_login_profile(self, *args, **kwargs):
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


class GroupLister(ResourceLister):
    prefix = "group_list"
    title = "Groups"
    command_palette = ["group", "groups"]

    def title_info(self):
        return "User: {0}".format(self.user["name"]) if self.user is not None else None

    def do_attach(self, policy_arn):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "attach_group_policy",
            {"GroupName": self.selection["name"], "PolicyArn": policy_arn},
            "Attach Managed Group Policy",
            "IAM",
            subcategory="Group",
            success_template="Attaching policy {PolicyArn} to group {GroupName}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def attach_policy(self, _):
        if self.selection is None:
            return
        SingleSelectorDialog(
            self.parent,
            "Attach policy to group",
            "policy",
            "attach",
            PolicyLister,
            self.do_attach,
            caller=self,
        )

    def create_group(self, _):
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

    def delete_group(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="group",
            resource_identifier=self.selection["name"],
            callback=self.do_delete,
            action_name="Delete",
        )

    def do_delete(self, **kwargs):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "delete_group",
            {"GroupName": self.selection["name"]},
            "Delete Group",
            "IAM",
            subcategory="Group",
            success_template="Deleting group {GroupName}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def remove_from_group(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="user",
            resource_identifier=self.user["name"],
            from_what="group",
            from_what_name=self.selection["name"],
            callback=self.do_remove,
            action_name="Remove",
        )

    def do_remove(self, **kwargs):
        if self.selection is None:
            return
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
        if self.selection is None:
            return
        SingleSelectorDialog(
            self.parent,
            "Add user to group",
            "user",
            "add",
            UserLister,
            self.do_add,
            caller=self,
        )

    def do_add(self, user):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "add_user_to_group",
            {"GroupName": self.selection["name"], "UserName": user},
            "Add User to Group",
            "IAM",
            subcategory="Group",
            success_template="Adding user {UserName} to group {GroupName}",
            resource=self.selection["name"],
        )

    def __init__(self, *args, user=None, **kwargs):
        self.resource_key = "iam"
        self.user = user
        self.list_method = "list_groups_for_user" if user is not None else "list_groups"
        self.item_path = ".Groups"
        self.list_kwargs = {"UserName": self.user["name"]} if user is not None else {}
        self.column_paths = {
            "name": ".GroupName",
            "id": ".GroupId",
            "path": ".Path",
        }
        self.imported_column_sizes = {
            "name": 25,
            "id": 15,
            "path": 40,
        }
        self.hidden_columns = {
            "arn": ".Arn",
        }
        self.describe_command = GroupDescriber.opener
        self.additional_commands = {
            "u": {
                "command": UserLister.opener,
                "selection_arg": "group",
                "tooltip": "List Group Users",
            },
            "m": {
                "command": PolicyLister.opener,
                "selection_arg": "group",
                "tooltip": "View Managed Policies",
            },
            "p": {
                "command": InlinePolicyLister.opener,
                "selection_arg": "data",
                "tooltip": "View Inline Policies",
                "kwargs": {
                    "datatype": "group",
                },
            },
        }

        self.imported_column_order = ["name", "id", "path"]
        self.sort_column = "name"
        super().__init__(*args, **kwargs)
        self.inliner = InlinePolicyAttacher(self, "group")
        self.add_hotkey("a", self.attach_policy, "Attach Policy")
        self.add_hotkey("c", self.create_group, "Create Group")
        self.add_hotkey("i", self.inliner.attach_inline_policy, "Put Inline Policy")
        if self.user is None:
            self.add_hotkey(ControlCodes.D, self.delete_group, "Delete Group")
            self.add_hotkey("j", self.add_user_to_group, "Add User")
        else:
            self.add_hotkey(ControlCodes.D, self.remove_from_group, "Remove from Group")


class GroupDescriber(Describer):
    prefix = "group_browser"
    title = "Group"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "iam"
        self.describe_method = "get_group"
        self.describe_kwarg_name = "GroupName"
        self.object_path = ".Group"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class PolicyLister(ResourceLister):
    prefix = "policy_list"
    title = "Policies"
    command_palette = ["policy", "policies"]

    def title_info(self):
        if self.user is not None:
            return "User: {0}".format(self.user["name"])
        elif self.group is not None:
            return "Group: {0}".format(self.group["name"])
        elif self.role is not None:
            return "Role: {0}".format(self.role["name"])
        else:
            return None

    def get_scope_tooltip(self):
        return "Change Scope ({0})".format(self.scope)

    def change_scope(self, *args):
        idx = self.scopes.index(self.scope)
        newidx = idx + 1
        if newidx >= len(self.scopes):
            newidx = 0
        self.scope = self.scopes[newidx]
        self.list_kwargs["Scope"] = self.scope
        Common.Session.set_message("Refreshing...", Common.color("message_info"))
        self.refresh_data()

    def create_policy(self, *args):
        creator = ListResourceDocumentCreator(
            "iam",
            "create_policy",
            None,
            as_json=["Tags"],
            initial_document={
                "PolicyName": "",
                "Path": "/",
                "PolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "",
                            "Effect": "Deny",
                            "Action": [""],
                            "Resource": "*",
                            "Condition": {},
                        }
                    ],
                },
                "Description": "",
                "Tags": [{"Key": "", "Value": ""}],
            },
        )
        creator.edit()
        self.refresh_data()

    def delete_policy(self, _):
        if "attached" not in self.selection or int(self.selection["attached"]) > 0:
            Common.Session.set_message(
                "Policy must be detached before deletion", Common.color("message_error")
            )
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="policy",
            resource_identifier=self.selection["name"],
            callback=self.do_delete,
            action_name="Delete",
        )

    def do_delete(self, **kwargs):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "delete_policy",
            {"PolicyArn": self.selection["arn"]},
            "Delete Policy",
            "IAM",
            subcategory="Policy",
            success_template="Deleting policy {PolicyArn}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def detach_policy(self, _):
        if self.selection is None:
            return
        if self.user is not None:
            dtype = "user"
            dname = self.user.name
        elif self.group is not None:
            dtype = "group"
            dname = self.group.name
        elif self.role is not None:
            dtype = "role"
            dname = self.role.name
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="policy",
            resource_identifier=self.selection["name"],
            from_what=dtype,
            from_what_name=dname,
            callback=self.do_detach,
            action_name="Detach",
        )

    def do_detach(self, **kwargs):
        if self.selection is None:
            return
        if self.user is not None:
            method = "detach_user_policy"
            arg_name = "UserName"
            arg_value = self.user.name
            resource = "user"
        elif self.group is not None:
            method = "detach_group_policy"
            arg_name = "GroupName"
            arg_value = self.group.name
            resource = "group"
        elif self.role is not None:
            method = "detach_role_policy"
            arg_name = "RoleName"
            arg_value = self.role.name
            resource = "role"
        else:
            return
        Common.generic_api_call(
            "iam",
            method,
            {"PolicyArn": self.selection["arn"], arg_name: arg_value},
            "Detach {0} Policy".format(resource.capitalize()),
            "IAM",
            subcategory="Policy",
            success_template="Detaching policy {PolicyArn} from {resource}",
            resource="{0} {1}".format(resource, arg_value),
        )
        self.refresh_data()

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

        self.column_paths = {
            "name": ".PolicyName",
            "arn": ".PolicyArn" if isset > 0 else ".Arn",
        }
        self.imported_column_sizes = {
            "name": 80,
            "arn": 80,
        }
        self.imported_column_order = ["name", "arn"]
        if isset == 0:
            self.column_paths["attached"] = ".AttachmentCount"
            self.imported_column_sizes["attached"] = 8
            self.imported_column_order.append("attached")

        self.describe_command = PolicyDescriber.opener

        self.sort_column = "name"
        super().__init__(*args, **kwargs)
        self.add_hotkey("c", self.create_policy, "Create new policy")
        if isset == 0:
            self.add_hotkey("s", self.change_scope, self.get_scope_tooltip)
            self.add_hotkey(ControlCodes.D, self.delete_policy, "Delete policy")
        else:
            self.add_hotkey(ControlCodes.D, self.detach_policy, "Detach policy")


class PolicyDescriber(Describer):
    prefix = "policy_browser"
    title = "Policy"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="arn", **kwargs
    ):
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
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class PolicyVersionDescriber(Describer):
    prefix = "policy_version_browser"
    title = "Policy Document"

    def title_info(self):
        return self.name

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        entry,
        *args,
        policy="",
        entry_key="arn",
        **kwargs
    ):
        self.resource_key = "iam"
        self.describe_method = "get_policy_version"
        self.object_path = ".PolicyVersion"
        self.arn = Common.Session.jq(".Arn").input(text=policy).first()
        self.name = Common.Session.jq(".PolicyName").input(text=policy).first()
        version = Common.Session.jq(".DefaultVersionId").input(text=policy).first()
        self.describe_kwargs = {"PolicyArn": self.arn, "VersionId": version}
        super().__init__(
            parent, alignment, dimensions, *args, entry=None, entry_key=None, **kwargs
        )


class InlinePolicyLister(ResourceLister):
    prefix = "inline_policy_list"
    title = "Inline Policies"

    def title_info(self):
        return "{0}: {1}".format(self.datatype.capitalize(), self.data["name"])

    def delete_policy(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="inline policy",
            resource_identifier=self.selection["name"],
            from_what=self.datatype,
            from_what_name=self.data["name"],
            callback=self.do_delete,
            action_name="Delete",
        )

    def do_delete(self, **kwargs):
        if self.selection is not None:
            try:
                self.delete(
                    PolicyName=self.selection["name"],
                    UserName=self.user["name"],
                )
                Common.Session.set_message(
                    "Deleting policy {0} from {2} {1}".format(
                        self.selection["name"], self.user["name"], self.datatype
                    ),
                    Common.color("message_success"),
                )
            except Exception as e:
                Common.Session.set_message(str(e), Common.color("message_error"))
        self.refresh_data()

    def edit_policy(self, _):
        if self.selection is None:
            return
        self.attacher.do_attach_inline(self.data["name"], selection_is_policy=True)

    def __init__(self, *args, datatype="", data=None, **kwargs):
        self.data = data
        self.datatype = datatype
        self.attacher = InlinePolicyAttacher(self, datatype)
        self.arg = "{0}Name".format(datatype.capitalize())
        self.resource_key = "iam"
        self.delete = getattr(
            Common.Session.service_provider("iam"), "delete_{0}_policy".format(datatype)
        )
        self.list_method = "list_{0}_policies".format(datatype)
        self.item_path = ".PolicyNames"
        self.list_kwargs = {self.arg: self.data["name"]}
        self.column_paths = {
            "name": ".",
        }
        self.imported_column_sizes = {
            "name": 25,
        }
        self.describe_command = InlinePolicyDescriber.opener
        self.describe_kwargs = {"datatype": datatype, "data": data}

        self.imported_column_order = ["name"]
        self.sort_column = "name"
        super().__init__(*args, **kwargs)
        self.add_hotkey(ControlCodes.D, self.delete_policy, "Delete Policy")
        self.add_hotkey("e", self.edit_policy, "Edit Policy")


class InlinePolicyDescriber(Describer):
    prefix = "user_inline_policy_browser"
    title = "Inline Policy"

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        entry,
        *args,
        entry_key="name",
        caller=None,
        datatype="",
        data=None,
        **kwargs
    ):
        self.resource_key = "iam"
        self.describe_method = "get_{0}_policy".format(datatype)
        self.arg = "{0}Name".format(datatype.capitalize())
        self.describe_kwarg_name = "PolicyName"
        self.describe_kwargs = {self.arg: data["name"]}
        self.object_path = "."
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            caller=caller,
            **kwargs
        )


class RoleLister(ResourceLister):
    prefix = "role_list"
    title = "Roles"
    command_palette = ["role", "roles"]

    def title_info(self):
        return (
            None
            if self.instanceprofile is None
            else "InstanceProfile: {0}".format(self.instanceprofile.name)
        )

    def create_role(self, _):
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

    def do_attach(self, policy_arn):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "attach_role_policy",
            {"PolicyArn": policy_arn, "RoleName": self.selection["name"]},
            "Attach Managed Role Policy",
            "IAM",
            subcategory="Role",
            success_template="Attaching policy {PolicyArn} to role {RoleName}",
            resource=self.selection["name"],
        )

    def attach_policy(self, _):
        if self.selection is None:
            return
        SingleSelectorDialog(
            self.parent,
            "Attach policy to role",
            "policy",
            "attach",
            PolicyLister,
            self.do_attach,
            caller=self,
        )

    def add_to_instance_profile(self, _):
        if self.selection is None:
            return
        SingleSelectorDialog(
            self.parent,
            "Add role to instance profile",
            "instance profile",
            "add",
            InstanceProfileLister,
            self.do_add,
            caller=self,
        )

    def do_add(self, ip):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "add_role_to_instance_profile",
            {"InstanceProfileName": ip, "RoleName": self.selection["name"]},
            "Add Role to Instance Profile",
            "IAM",
            subcategory="Role",
            success_template="Adding role {RoleName} to instance profile {InstanceProfileName}",
            resource=self.selection["name"],
        )

    def detach_from_instance_profile(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="role",
            resource_identifier=self.selection["name"],
            from_what="instance profile",
            from_what_name=self.instanceprofile["name"],
            callback=self.do_detach,
            action_name="Detach",
        )

    def do_detach(self, **kwargs):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "remove_role_from_instance_profile",
            {
                "InstanceProfileName": self.instanceprofile["name"],
                "RoleName": self.selection["name"],
            },
            "Remove Role from Instance Profile",
            "IAM",
            subcategory="Role",
            success_template="Removing role {RoleName} from instance profile {InstanceProfileName}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def delete_role(self, _):
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="role",
            resource_identifier=self.selection["name"],
            callback=self.do_delete,
            action_name="Delete",
        )

    def do_delete(self, **kwargs):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "delete_role",
            {"RoleName": self.selection["name"]},
            "Delete Role",
            "IAM",
            subcategory="Role",
            success_template="Deleting role {RoleName}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def __init__(self, *args, instanceprofile=None, **kwargs):
        self.instanceprofile = instanceprofile
        self.resource_key = "iam"
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
        self.column_paths = {
            "name": ".RoleName",
            "id": ".RoleId",
            "path": ".Path",
        }
        self.imported_column_sizes = {
            "name": 25,
            "id": 15,
            "path": 40,
        }
        self.hidden_columns = {
            "arn": ".Arn",
        }
        self.describe_command = RoleDescriber.opener
        self.additional_commands = {
            "m": {
                "command": PolicyLister.opener,
                "selection_arg": "role",
                "tooltip": "View Managed Policies",
            },
            "p": {
                "command": InlinePolicyLister.opener,
                "selection_arg": "data",
                "tooltip": "View Inline Policies",
                "kwargs": {
                    "datatype": "role",
                },
            },
            "n": {
                "command": InstanceProfileLister.opener,
                "selection_arg": "role",
                "tooltip": "View Instance Profiles",
            },
        }

        self.imported_column_order = ["name", "id", "path"]
        self.sort_column = "name"
        super().__init__(*args, **kwargs)
        self.inliner = InlinePolicyAttacher(self, "role")
        self.add_hotkey("a", self.attach_policy, "Attach Policy")
        self.add_hotkey("c", self.create_role, "Create Role")
        self.add_hotkey("i", self.inliner.attach_inline_policy, "Put Inline Policy")
        if self.instanceprofile is None:
            self.add_hotkey(
                "j", self.add_to_instance_profile, "Add to Instance Profile"
            )
            self.add_hotkey(
                ControlCodes.D,
                self.delete_role,
                "Delete Role",
            )
        else:
            self.add_hotkey(
                ControlCodes.D,
                self.detach_from_instance_profile,
                "Detach from Instance Profile",
            )


class RoleDescriber(Describer):
    prefix = "role_browser"
    title = "Role"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "iam"
        self.describe_method = "get_role"
        self.describe_kwarg_name = "RoleName"
        self.object_path = ".Role"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class InstanceProfileLister(ResourceLister):
    prefix = "instance_profile_list"
    title = "Instance Profiles"
    command_palette = ["instanceprofile", "instanceprofiles"]

    def title_info(self):
        return None if self.role is None else "Role: {0}".format(self.role["name"])

    def determine_role_count(self, instanceprofile):
        return str(len(instanceprofile["Roles"])) if "Roles" in instanceprofile else 0

    def add_role(self, _):
        if self.selection is None:
            return
        SingleSelectorDialog(
            self.parent,
            "Add role to instance profile",
            "role",
            "add",
            RoleLister,
            self.do_add,
            caller=self,
        )

    def do_add(self, role):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "add_role_to_instance_profile",
            {"InstanceProfileName": self.selection["name"], "RoleName": role},
            "Add Role to Instance Profile",
            "IAM",
            subcategory="Role",
            success_template="Adding role {RoleName} to instance profile {InstanceProfileName}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def remove_from_role(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="role",
            resource_identifier=self.role["name"],
            from_what="instance profile",
            from_what_name=self.selection["name"],
            callback=self.do_detach,
            action_name="Detach",
        )

    def do_detach(self, **kwargs):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "remove_role_from_instance_profile",
            {
                "RoleName": self.role["name"],
                "InstanceProfileName": self.selection["name"],
            },
            "Remove Role from Instance Profile",
            "IAM",
            subcategory="Instance Profile",
            success_template="Removing to role {RoleName} from instance profile {InstanceProfileName}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def delete_instance_profile(self, _):
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="instance profile",
            resource_identifier=self.selection["name"],
            callback=self.do_delete,
            action_name="Delete",
        )

    def do_delete(self, **kwargs):
        if self.selection is None:
            return
        Common.generic_api_call(
            "iam",
            "delete_instance_profile",
            {
                "InstanceProfileName": self.selection["name"],
            },
            "Delete Instance Profile",
            "IAM",
            subcategory="Instance Profile",
            success_template="Deleting instance profile {InstanceProfileName}",
            resource=self.selection["name"],
        )
        self.refresh_data()

    def __init__(self, *args, role=None, **kwargs):
        self.role = role
        self.resource_key = "iam"
        self.list_method = (
            "list_instance_profiles"
            if self.role is None
            else "list_instance_profiles_for_role"
        )
        self.list_kwargs = {} if self.role is None else {"RoleName": self.role["name"]}
        self.item_path = ".InstanceProfiles"
        self.column_paths = {
            "name": ".InstanceProfileName",
            "id": ".InstanceProfileId",
            "path": ".Path",
            "roles": self.determine_role_count,
        }
        self.imported_column_sizes = {
            "name": 25,
            "id": 15,
            "path": 40,
            "roles": 5,
        }
        self.hidden_columns = {
            "arn": ".Arn",
        }
        self.describe_command = InstanceProfileDescriber.opener
        self.open_command = "o"
        self.additional_commands = {
            # "i": {
            #    "tooltip": "View Instances",
            # },
            # "l": {
            #    "tooltip": "View Launch Configurations",
            # },
            "o": {
                "command": RoleLister.opener,
                "selection_arg": "instanceprofile",
                "tooltip": "View Roles",
            },
        }

        self.imported_column_order = ["name", "id", "path", "roles"]
        self.sort_column = "name"
        super().__init__(*args, **kwargs)
        if self.role is None:
            self.add_hotkey("j", self.add_role, "Attach Role")
            self.add_hotkey(
                ControlCodes.D, self.delete_instance_profile, "Delete Instance Profile"
            )
        else:
            self.add_hotkey(
                ControlCodes.D, self.remove_from_role, "Detach Instance Profile"
            )


class InstanceProfileDescriber(Describer):
    prefix = "instance_profile_browser"
    title = "Instance Profile"

    def populate_entry(self, *args, entry, entry_key, **kwargs):
        import sys

        print("{0} {1}".format(entry, entry_key), file=sys.stderr)
        super().populate_entry(*args, entry=entry, entry_key=entry_key, **kwargs)

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        from .arn import ARN

        self.resource_key = "iam"
        self.describe_method = "get_instance_profile"
        self.describe_kwarg_name = "InstanceProfileName"
        self.object_path = ".InstanceProfile"
        if entry_key == "id":  # id is an Arn from a single relation lister
            arn = ARN(entry["id"])
            entry_key = "name"
            entry["name"] = arn.resource_id_first
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
