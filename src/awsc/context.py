"""
Module which contains AWS context-related resources.

Contexts are keypairs able to access different AWS accounts.
"""
from botocore import exceptions as botoerror

from .base_control import DeleteResourceDialog, OpenableListControl
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
        self.set_title_label("Enter AWS context details")
        self.name_field = DialogFieldText(
            "Name:",
            label_min=16,
            color=Common.color(
                "context_add_modal_dialog_textfield", "modal_dialog_textfield"
            ),
            selected_color=Common.color(
                "context_add_modal_dialog_textfield_selected",
                "modal_dialog_textfield_selected",
            ),
            label_color=Common.color(
                "context_add_modal_dialog_textfield_label",
                "modal_dialog_textfield_label",
            ),
        )
        self.add_field(self.name_field)
        self.access_key_field = DialogFieldText(
            "Access key:",
            label_min=16,
            color=Common.color(
                "context_add_modal_dialog_textfield", "modal_dialog_textfield"
            ),
            selected_color=Common.color(
                "context_add_modal_dialog_textfield_selected",
                "modal_dialog_textfield_selected",
            ),
            label_color=Common.color(
                "context_add_modal_dialog_textfield_label",
                "modal_dialog_textfield_label",
            ),
        )
        self.add_field(self.access_key_field)
        self.secret_key_field = DialogFieldText(
            "Secret key:",
            label_min=16,
            color=Common.color(
                "context_add_modal_dialog_textfield", "modal_dialog_textfield"
            ),
            selected_color=Common.color(
                "context_add_modal_dialog_textfield_selected",
                "modal_dialog_textfield_selected",
            ),
            label_color=Common.color(
                "context_add_modal_dialog_textfield_label",
                "modal_dialog_textfield_label",
            ),
            password=True,
        )
        self.add_field(self.secret_key_field)
        self.caller = caller

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
            self.name_field.text,
            sts["Account"],
            self.access_key_field.text,
            self.secret_key_field.text,
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

        self.reload_contexts()

    def reload_contexts(self):
        """
        Refreshes the list of contexts from configuration.
        """
        self.entries = []
        for context, data in Common.Configuration["contexts"].items():
            self.add_entry(
                ListEntry(
                    context,
                    **{
                        "account id": data["account_id"],
                        "default": "✓"
                        if context == Common.Configuration["default_context"]
                        else " ",
                    }
                )
            )
        if 0 <= self.selected < len(self.entries):
            return
        try:
            self.selected = (
                Common.Configuration["contexts"]
                .keys()
                .index(Common.Configuration["default_context"])
            )
        except ValueError:
            self.selected = 0

    @OpenableListControl.Autohotkey("a", "Add new context")
    def add_new_context(self, _):
        """
        Hotkey callback for adding a new context.
        """
        AddContextDialog.opener(caller=self)

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
        if self.selection is not None:
            Common.Configuration["default_context"] = self.selection.name
            Common.Configuration.write_config()
            self.reload_contexts()

    @OpenableListControl.Autohotkey("KEY_ENTER", "Select", True)
    def select_context(self, _):
        """
        Hotkey callback for setting the active context.
        """
        if self.selection is not None:
            Common.Session.context = self.selection.name

    @OpenableListControl.Autohotkey(ControlCodes.D, "Delete context", True)
    def delete_selected_context(self, _):
        """
        Hotkey callback for deleting the selected context.
        """
        if self.selection is not None:
            DeleteResourceDialog.opener(
                caller=self,
                resource_type="context",
                resource_identifier=self.selection["name"],
                callback=self.do_delete,
            )

    def do_delete(self):
        """
        Action callback for the context deletion dialog.
        """
        Common.Configuration.delete_context(self.selection["name"])
        self.reload_contexts()
