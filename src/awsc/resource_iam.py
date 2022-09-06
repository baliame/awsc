"""
Module for common elements for IAM resources.
"""
from copy import deepcopy

from botocore import exceptions as botoerror

from .base_control import (
    Describer,
    ListResourceDocumentCreator,
    ResourceLister,
    SelectionAttribute,
    SingleNameDialog,
    TemplateDict,
)
from .common import Common
from .termui.common import Commons
from .termui.ui import ControlCodes

EMPTY_POLICY_DOCUMENT = {
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
"""
Anatomy of an empty policy document.
"""


class InlinePolicyAttacher:
    """
    Helper class for attaching inline policies to the big 3 IAM types - users, groups and roles.

    Attributes
    ----------
    datatype : str
        The type of data (user, role or group).
    parent : awsc.termui.control.Control
        The control using the attacher.
    client : object
        Boto3 service provider.
    get : callable
        Method reference to the datatype policy getter of self.client.
    put_method : str
        Method name for the datatype policy setter of self.client.
    arg : str
        The argname for the put_method.
    selection_is_policy : bool, default=False
        Whether the parent is listing policies rather than resources that receive policies.
    """

    def __init__(self, parent, datatype, selection_is_policy=False):
        self.datatype = datatype
        self.parent = parent
        self.client = Common.Session.service_provider("iam")

        self.get = getattr(self.client, f"get_{datatype}_policy")
        self.put_method = f"put_{datatype}_policy"
        self.arg = f"{datatype.capitalize()}Name"

        self.selection_is_policy = selection_is_policy

        if not selection_is_policy:
            self.parent.add_hotkey(
                "i", self.attach_inline_policy, "Put inline policy", True
            )

    def attach_inline_policy(self, _):
        """
        Hotkey callback for attaching an inline policy to the resource listed by the parent.
        """
        SingleNameDialog(
            self.parent.parent,
            f"Attach new or edit existing inline policy for {self.datatype}",
            self.do_attach_inline,
            label="Policy name:",
            what="name",
            subject="policy",
            default="",
            caller=self.parent,
            accepted_inputs=Commons.alphanum_with_symbols("+=,.@_-"),
        )

    def do_attach_inline(self, name):
        """
        Action callback for attaching an inline policy.

        Parameters
        ----------
        name : str
            The name of the resource not managed by the lister parent. This is a policy name if self.selection_is_policy is False,
            otherwise a role/user/group name.
        """
        if self.parent.selection is None:
            return
        if self.selection_is_policy:
            kwargs = {"PolicyName": self.parent.selection["name"], self.arg: name}
        else:
            kwargs = {self.arg: self.parent.selection["name"], "PolicyName": name}
        try:
            chk = self.get(**kwargs)
            initial_document = {"PolicyDocument": chk["PolicyDocument"]}
        except self.client.exceptions.NoSuchEntityException:
            initial_document = deepcopy(EMPTY_POLICY_DOCUMENT)
        except botoerror.ClientError as error:
            Common.clienterror(
                error,
                f"Retrieve Inline {self.datatype.capitalize()} Policy",
                "IAM",
                set_message=True,
            )
            return
        except Exception as error:
            Common.error(
                str(error),
                f"Retrieve Inline {self.datatype.capitalize()} Policy",
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


class InlinePolicyDescriber(Describer):
    """
    Describer control for inline policies.
    """

    prefix = "user_inline_policy_browser"
    title = "Inline Policy"

    def __init__(self, *args, caller=None, datatype="", data=None, **kwargs):
        self.resource_key = "iam"
        self.describe_method = f"get_{datatype}_policy"
        self.arg = f"{datatype.capitalize()}Name"
        self.describe_kwarg_name = "PolicyName"
        self.describe_kwargs = {self.arg: data["name"]}
        self.object_path = "."
        super().__init__(*args, caller=caller, **kwargs)


@ResourceLister.Autocommand(
    "UserLister", "p", "View inline policies", "data", datatype="user"
)
@ResourceLister.Autocommand(
    "GroupLister", "p", "View inline policies", "data", datatype="group"
)
@ResourceLister.Autocommand(
    "RoleLister", "p", "View inline policies", "data", datatype="role"
)
class InlinePolicyLister(ResourceLister):
    """
    Lister control for inline policies.
    """

    prefix = "inline_policy_list"
    title = "Inline Policies"

    resource_type = "inline policy"
    main_provider = "iam"
    category = "IAM"
    subcategory = "Inline Policies"
    columns = {
        "name": {
            "path": ".",
            "size": 25,
            "weight": 0,
            "sort_weight": 0,
        },
    }
    describe_command = InlinePolicyDescriber.opener

    def title_info(self):
        return f"{self.datatype.capitalize()}: {self.data['name']}"

    @ResourceLister.Autohotkey("e", "Edit Policy", True)
    def edit_policy(self, _):
        """
        Hotkey callback for editing an inline policy.
        """
        self.attacher.do_attach_inline(self.data["name"])

    def __init__(self, *args, datatype="", data=None, **kwargs):
        self.data = data
        self.datatype = datatype
        self.attacher = InlinePolicyAttacher(self, datatype, selection_is_policy=True)
        self.arg = f"{datatype.capitalize()}Name"
        self.resource_key = "iam"
        self.delete_method = f"delete_{datatype}_policy"
        self.list_method = f"list_{datatype}_policies"
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
        self.confirm_template(
            self.delete_method,
            TemplateDict(
                {"PolicyName": SelectionAttribute("name"), self.arg: self.data["name"]}
            ),
            hotkey=ControlCodes.D,
            hotkey_tooltip="Delete Policy",
        )
