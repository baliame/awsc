"""
Module which contains AWS context-related resources.

Contexts are keypairs able to access different AWS accounts.
"""
import configparser
import datetime
import sys
from pathlib import Path

from botocore import exceptions as botoerror

from .base_control import (
    DeleteResourceDialog,
    DialogFieldResourceListSelector,
    OpenableListControl,
)
from .common import Common, SessionAwareDialog
from .termui.control import Border
from .termui.dialog import DialogFieldLabel, DialogFieldText
from .termui.list_control import ListEntry
from .termui.ui import ControlCodes


class ImportContextDialog(SessionAwareDialog):
    """
    Dialog control for importing a context from the environment.

    Attributes
    ----------
    caller : awsc.termui.control.Control
        Parent control which controls this dialog.
    error_label : awsc.termui.dialog.DialogFieldLabel
        Error label for displaying validation errors.
    name_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the name of the context.
    access_key : str
        The access key being imported.
    secret_key : str
        The secret key being imported.
    access_key_field : awsc.termui.dialog.DialogFieldLabel
        Field for displaying the access key being imported.
    secret_key_field : awsc.termui.dialog.DialogFieldLabel
        Field for displaying that a secret key is being imported. It is masked.
    """

    line_size = 20

    def __init__(self, parent, alignment, dimensions, *args, caller=None, **kwargs):
        self.accepts_inputs = True
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            "New Context",
            Common.color("modal_dialog_border_title"),
        )
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        super().__init__(parent, alignment, dimensions, caller=caller, *args, **kwargs)
        self.caller = caller
        self.set_title_label("Enter AWS context details")
        self.name_field = DialogFieldText(
            "Name:", **Common.textfield_colors("context_add")
        )
        self.add_field(self.name_field)
        creds = Common.Session.service_provider.env_session().get_credentials()
        if creds is None or not creds.access_key or not creds.secret_key:
            Common.Session.set_message(
                "No valid credentials in environment.", Common.color("message_error")
            )
            self.close()
            return
        self.access_key = creds.access_key
        self.secret_key = creds.secret_key
        self.access_key_field = DialogFieldLabel(
            [
                ("Access key: ", Common.color("generic")),
                (creds.access_key, Common.color("highlight")),
            ],
            centered=False,
        )
        self.add_field(self.access_key_field)
        self.secret_key_field = DialogFieldLabel(
            [
                ("Secret key: ", Common.color("generic")),
                ("*" * len(creds.secret_key), Common.color("highlight")),
            ],
            centered=False,
        )
        self.add_field(self.secret_key_field)

    def input(self, key):
        if not self.accepts_inputs:
            return True
        if key.is_sequence and key.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(key)

    def accept_and_close(self):
        if self.name_field.text == "":
            self.error_label.text = "Name cannot be blank."
            return
        try:
            sts = Common.Session.service_provider.whoami(
                keys={"access": self.access_key, "secret": self.secret_key}
            )
        except botoerror.ClientError as error:
            self.error_label.text = "Key verification failed"
            Common.clienterror(
                error,
                "Key verification failed",
                "Core",
                subcategory="STS",
                resource=self.access_key,
                set_message=False,
                access_key=self.access_key,
                secret_key="<PRESENT>",
            )
            return

        self.accepts_inputs = False

        Common.Configuration.add_or_edit_context(
            self.name_field.text, sts["Account"], self.access_key, self.secret_key
        )
        self.close()

    def close(self):
        if self.caller is not None:
            self.caller.reload_contexts()
        super().close()


def _context_color_defaults():
    return {
        "color": Common.color(
            "context_add_modal_dialog_textfield", "modal_dialog_textfield"
        ),
        "selected_color": Common.color(
            "context_add_modal_dialog_textfield_selected",
            "modal_dialog_textfield_selected",
        ),
        "label_color": Common.color(
            "context_add_modal_dialog_textfield_label",
            "modal_dialog_textfield_label",
        ),
    }


class MFADialog(SessionAwareDialog):
    """
    Dialog control for multi-factor authentication.

    Attributes
    ----------
    caller : awsc.termui.control.Control
        Parent control which controls this dialog.
    error_label : awsc.termui.dialog.DialogFieldLabel
        Error label for displaying validation errors.
    token_field : aws.termui.dialog.DialogFieldText
        Field for entering the MFA token.
    """

    line_size = 20

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        caller=None,
        **kwargs,
    ):
        self.accepts_inputs = True
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            "Authenticate context",
            Common.color("modal_dialog_border_title"),
        )
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        super().__init__(parent, alignment, dimensions, caller=caller, *args, **kwargs)
        self.set_title_label(
            f"Enter MFA token code for {Common.Session.context_data['mfa_device']}"
        )
        self.token_field = DialogFieldText(
            "MFA Token:", label_min=16, **_context_color_defaults()
        )
        self.add_field(self.token_field)

    def accept_and_close(self):
        if self.token_field.text == "":
            self.error_label.text = "Token cannot be blank."
            return
        keys = Common.Session.context_perm_auth
        resp = Common.generic_api_call(
            "sts",
            "get_session_token",
            {
                "DurationSeconds": 86400,
                "SerialNumber": Common.Session.context_data["mfa_device"],
                "TokenCode": self.token_field.text,
            },
            "Retrieve session token",
            "STS",
            keys=keys,
        )
        if not resp["Success"]:
            self.error_label.text = "Failed to acquire security credentials."
            return
        creds = resp["Response"]["Credentials"]
        Common.Configuration.keystore.set_temp(
            Common.Session.context,
            {
                "access": creds["AccessKeyId"],
                "secret": creds["SecretAccessKey"],
                "session": creds["SessionToken"],
                "expiry": creds["Expiration"].timestamp(),
                "mfa_device": Common.Session.context_data["mfa_device"],
            },
        )

        self.accepts_inputs = False
        Common.Session.context = Common.Session.context
        self.close()

    def close(self):
        if self.caller is not None:
            self.caller.reload_contexts()
        super().close()


class AddContextDialog(SessionAwareDialog):
    """
    Dialog control for adding a new context.

    Attributes
    ----------
    caller : awsc.termui.control.Control
        Parent control which controls this dialog.
    error_label : awsc.termui.dialog.DialogFieldLabel
        Error label for displaying validation errors.
    name_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the name of the context.
    access_key_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the access key.
    secret_key_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the secret key.
    """

    line_size = 20

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        caller=None,
        existing_context=None,
        **kwargs,
    ):
        from .resource_iam_user import MFADeviceLister

        self.accepts_inputs = True
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            f"{'New' if existing_context is None else 'Edit'} Context",
            Common.color("modal_dialog_border_title"),
        )
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        super().__init__(parent, alignment, dimensions, caller=caller, *args, **kwargs)
        self.editing = existing_context
        self.set_title_label("Enter AWS context details")
        self.name_field = (
            DialogFieldText(
                "Name:",
                label_min=16,
                **_context_color_defaults(),
            )
            if existing_context is None
            else DialogFieldLabel(
                [
                    ("Name: ", Common.color("generic")),
                    (existing_context, Common.color("highlight")),
                ],
                centered=False,
            )
        )
        keys = (
            {"access": "", "secret": ""}
            if existing_context is None
            else Common.Configuration.keystore.get_permanent_credentials(
                existing_context
            )
        )
        self.add_field(self.name_field)
        self.access_key_field = DialogFieldText(
            "Access key:",
            text=keys["access"],
            label_min=16,
            **_context_color_defaults(),
        )
        self.add_field(self.access_key_field)
        self.secret_key_field = DialogFieldText(
            "Secret key:",
            text=keys["secret"],
            label_min=16,
            **_context_color_defaults(),
            password=True,
        )
        self.add_field(self.secret_key_field)
        mfa_device = (
            ""
            if existing_context is None
            else Common.Configuration["contexts"][existing_context]["mfa_device"]
        )
        self.mfa_device_field = DialogFieldResourceListSelector(
            MFADeviceLister,
            "MFA device:",
            default=mfa_device,
            label_min=16,
            **_context_color_defaults(),
        )
        self.add_field(self.mfa_device_field)
        self.caller = caller

    def input(self, key):
        if not self.accepts_inputs:
            return True
        if key.is_sequence and key.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(key)

    def accept_and_close(self):
        if self.editing is None:
            if self.name_field.text == "":
                self.error_label.text = "Name cannot be blank."
                return
            if self.name_field.text == "localstack":
                self.error_label.text = (
                    'The name "localstack" is protected and cannot be used.'
                )
                return
        if self.access_key_field.text == "":
            self.error_label.text = "Access key cannot be blank."
            return
        if self.secret_key_field.text == "":
            self.error_label.text = "Secret key cannot be blank."
            return
        try:
            sts = Common.Session.service_provider.whoami(
                keys={
                    "access": self.access_key_field.text,
                    "secret": self.secret_key_field.text,
                }
            )
        except botoerror.ClientError as error:
            self.error_label.text = "Key verification failed"
            Common.clienterror(
                error,
                "Key verification failed",
                "Core",
                subcategory="STS",
                resource=self.access_key_field.text,
                set_message=False,
                access_key=self.access_key_field.text,
                secret_key="<PRESENT>",
            )
            return

        self.accepts_inputs = False

        Common.Configuration.add_or_edit_context(
            self.name_field.text if self.editing is None else self.editing,
            sts["Account"],
            self.access_key_field.text,
            self.secret_key_field.text,
            self.mfa_device_field.text,
        )
        self.close()

    def close(self):
        if self.caller is not None:
            self.caller.reload_contexts()
        super().close()


class AddRoleContextDialog(SessionAwareDialog):
    """
    Dialog control for adding a new context.

    Attributes
    ----------
    caller : awsc.termui.control.Control
        Parent control which controls this dialog.
    error_label : awsc.termui.dialog.DialogFieldLabel
        Error label for displaying validation errors.
    name_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the name of the context.
    source_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the name of the source context.
    role_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the role to assume.
    """

    line_size = 20

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        caller=None,
        existing_context=None,
        **kwargs,
    ):
        from .resource_iam_role import RoleLister

        self.accepts_inputs = True
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            f"{'New' if existing_context is None else 'Edit'} Context",
            Common.color("modal_dialog_border_title"),
        )
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        super().__init__(parent, alignment, dimensions, caller=caller, *args, **kwargs)
        self.editing = existing_context
        self.set_title_label("Enter AWS context details")
        self.name_field = (
            DialogFieldText("Name:", label_min=16, **_context_color_defaults())
            if existing_context is None
            else DialogFieldLabel(
                [
                    ("Name: ", Common.color("generic")),
                    (existing_context, Common.color("highlight")),
                ],
                centered=False,
            )
        )
        self.add_field(self.name_field)
        source = (
            ""
            if existing_context is None
            else Common.Configuration.keystore.get_ref_name(existing_context)
        )
        self.source_field = DialogFieldResourceListSelector(
            ContextList,
            "Source context:",
            default=source,
            label_min=16,
            **_context_color_defaults(),
        )
        self.add_field(self.source_field)

        role = (
            ""
            if existing_context is None
            else Common.Configuration["contexts"][existing_context]["role"]
        )
        self.role_field = DialogFieldResourceListSelector(
            RoleLister,
            "IAM role to assume:",
            default=role,
            label_min=16,
            **_context_color_defaults(),
        )
        self.add_field(self.role_field)
        self.caller = caller

    def input(self, key):
        if not self.accepts_inputs:
            return True
        if key.is_sequence and key.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(key)

    def accept_and_close(self):
        if self.editing is None:
            if self.name_field.text == "":
                self.error_label.text = "Name cannot be blank."
                return
            if self.name_field.text == "localstack":
                self.error_label.text = (
                    'The name "localstack" is protected and cannot be used.'
                )
                return
        if self.source_field.text == "":
            self.error_label.text = "Source context cannot be blank."
            return
        if self.role_field.text == "":
            self.error_label.text = "IAM Role cannot be blank."
            return

        ctx = Common.Configuration.keystore.get_permanent_credentials(
            self.source_field.text
        )
        sts = Common.Session.service_provider.whoami(keys=ctx)

        Common.Configuration.add_or_edit_role_context(
            self.name_field.text if self.editing is None else self.editing,
            sts["Account"],
            self.source_field.text,
            self.role_field.text,
            mfa_device="",
        )
        self.close()

    def close(self):
        if self.caller is not None:
            self.caller.reload_contexts()
        super().close()


class ContextList(OpenableListControl):
    """
    Lister control for contexts.
    """

    prefix = "context_list"
    title = "Contexts"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_column("account id", 12)
        self.add_column("default", 7)
        self.add_column("type", 4)

        self.jump_cursor = True
        self.reload_contexts()
        self.jump_cursor = False

        if self.selector_cb is None:
            if Common.Session.context != "":
                self.select_context(self, initial=True)

    def reload_contexts(self):
        """
        Refreshes the list of contexts from configuration.
        """
        self.entries = []
        idx = 0
        for context, data in Common.Configuration["contexts"].items():
            self.add_entry(
                ListEntry(
                    context,
                    **{
                        "account id": data["account_id"],
                        "default": "✓"
                        if context == Common.Configuration["default_context"]
                        else " ",
                        "type": "key pair" if data["role"] == "" else "role",
                    },
                )
            )
            if self.jump_cursor and context == Common.Configuration["default_context"]:
                self.selected = idx
            idx += 1
        if 0 <= self.selected < len(self.entries):
            return
        self.selected = 0

    @OpenableListControl.Autohotkey("a", "Add key context")
    def add_new_context(self, _):
        """
        Hotkey callback for adding a new context.
        """
        AddContextDialog.opener(caller=self)

    @OpenableListControl.Autohotkey("s", "Add role context")
    def add_role_context(self, _):
        """
        Hotkey callback for adding a new role context.
        """
        AddRoleContextDialog.opener(caller=self)

    @OpenableListControl.Autohotkey("e", "Edit context", True)
    def edit_context(self, _):
        """
        Hotkey callback for adding a new context.
        """
        if self.selection["name"] == "localstack":
            Common.Session.set_message(
                "Cannot edit localstack context", Common.color("message_error")
            )
            return
        if self.selection["type"] == "key pair":
            AddContextDialog.opener(
                caller=self, existing_context=self.selection["name"]
            )
        elif self.selection["type"] == "role":
            AddRoleContextDialog.opener(
                caller=self, existing_context=self.selection["name"]
            )

    @OpenableListControl.Autohotkey("x", "Export context", True)
    def export_context(self, _):
        """
        Hotkey callback for exporting a context to .aws credentials. Performs MFA if necessary to export an authenticated context.
        """
        mfa_device = Common.Configuration["contexts"][self.selection["name"]][
            "mfa_device"
        ]
        extra_fields = {
            "label_overwrite": DialogFieldLabel(
                "This will overwrite the AWS profile with the same name.",
                Common.color("modal_dialog_error"),
            )
        }
        if mfa_device != "":
            extra_fields["mfa_device"] = DialogFieldLabel(
                f"Enter a code from MFA device {mfa_device}",
                Common.color("modal_dialog_textfield_label"),
            )
            extra_fields["mfa_code"] = DialogFieldText(
                "MFA code: ", label_min=16, **_context_color_defaults()
            )
        DeleteResourceDialog.opener(
            caller=self,
            resource_type="context",
            resource_identifier=self.selection["name"],
            action_name="export",
            extra_fields=extra_fields,
            callback=self.do_export,
        )

    def do_export(self, **kwargs):
        """
        Callback for confirmation of context export.
        """
        aws_creds = Path.home() / ".aws" / "credentials"
        try:
            with aws_creds.open("r", encoding="utf-8") as file:
                creds = file.read()
        except OSError as error:
            if error.errno == 2:  # FNF
                creds = ""
            else:
                print(
                    f"Failed to open ~/.aws/credentials: {str(error)}",
                    file=sys.stderr,
                )
                return
        keys = Common.Configuration.keystore.get_permanent_credentials(
            self.selection["name"]
        )
        parser = configparser.ConfigParser(default_section="__default")
        parser.read_string(creds)
        if parser.has_section(self.selection["name"]):
            parser.remove_section(self.selection["name"])
        parser.add_section(self.selection["name"])
        mfa_device = Common.Configuration["contexts"][self.selection["name"]][
            "mfa_device"
        ]
        if mfa_device != "":
            parser.set(self.selection["name"], "aws_mfa_device", mfa_device)
            resp = Common.generic_api_call(
                "sts",
                "get_session_token",
                {
                    "DurationSeconds": 86400,
                    "SerialNumber": mfa_device,
                    "TokenCode": kwargs["mfa_code"].value,
                },
                "Retrieve session token",
                "STS",
                keys=keys,
            )
            if not resp["Success"]:
                Common.Session.set_message(
                    "Error fetching security credentials", Common.color("message_error")
                )
                return
            token = resp["Response"]["Credentials"]["SessionToken"]
            expiration = resp["Response"]["Credentials"]["Expiration"]
            parser.set(self.selection["name"], "aws_session_token", token)
            parser.set(self.selection["name"], "aws_security_token", token)
            parser.set(
                self.selection["name"],
                "expiration",
                expiration.strftime("%Y-%m-%d %H:%M:%S"),
            )
            parser.set(
                self.selection["name"],
                "aws_access_key_id",
                resp["Response"]["Credentials"]["AccessKeyId"],
            )
            parser.set(
                self.selection["name"],
                "aws_secret_access_key",
                resp["Response"]["Credentials"]["SecretAccessKey"],
            )
        else:
            parser.set(self.selection["name"], "aws_access_key_id", keys["access"])
            parser.set(self.selection["name"], "aws_secret_access_key", keys["secret"])
        with aws_creds.open("w", encoding="utf-8") as file:
            parser.write(file)

    @OpenableListControl.Autohotkey("i", "Import context")
    def import_context(self, _):
        """
        Hotkey callback for importing a context.
        """
        ImportContextDialog.opener(caller=self)

    @OpenableListControl.Autohotkey("d", "Set as default", True)
    def set_default_context(self, _):
        """
        Hotkey callback for setting the default context.
        """
        if self.selection["type"] == "role":
            Common.Session.set_message(
                "Cannot set a role as a default context, sorry",
                Common.color("message_error"),
            )
            return
        Common.Configuration["default_context"] = self.selection.name
        Common.Configuration.write_config()
        self.reload_contexts()

    @OpenableListControl.Autohotkey("KEY_ENTER", "Select", True)
    def select_context(self, _, initial=False):
        """
        Hotkey callback for setting the active context.
        """
        if self.selection["type"] == "role":
            Common.Session.set_message(
                "Cannot assume roles yet", Common.color("message_error")
            )
            return
        Common.Session.context = self.selection.name
        if Common.Session.context_data["mfa_device"] != "" and (
            "mfa_device" not in Common.Session.context_auth
            or Common.Session.context_auth["mfa_device"]
            != Common.Session.context_data["mfa_device"]
            or "expiry" not in Common.Session.context_auth
            or datetime.datetime.now()
            > datetime.datetime.fromtimestamp(Common.Session.context_auth["expiry"])
        ):
            if initial:
                self.on_become_frame_hooks.append((MFADialog.opener, {"caller": self}))
            else:
                MFADialog.opener(caller=self)

    @OpenableListControl.Autohotkey(ControlCodes.D, "Delete context", True)
    def delete_selected_context(self, _):
        """
        Hotkey callback for deleting the selected context.
        """
        if self.selection.name == "localstack":
            Common.Session.set_message(
                "Cannot delete localstack context", Common.color("message_error")
            )
            return
        if self.selection.name in Common.Configuration.keystore.get_all_ref_targets():
            Common.Session.set_message(
                "Cannot delete context because context is referenced by another context.",
                Common.color("message_error"),
            )
            return
        DeleteResourceDialog.opener(
            caller=self,
            resource_type="context",
            resource_identifier=self.selection["name"],
            callback=self.do_delete,
        )

    def do_delete(self, **kwargs):
        """
        Action callback for the context deletion dialog.
        """
        Common.Configuration.delete_context(self.selection["name"])
        self.reload_contexts()
