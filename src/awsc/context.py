from botocore import exceptions

from .common import Common, SessionAwareDialog
from .info import HotkeyDisplay
from .termui.alignment import CenterAnchor, Dimension, TopRightAnchor
from .termui.control import Border
from .termui.dialog import DialogFieldLabel, DialogFieldText
from .termui.list_control import ListControl, ListEntry


class DeleteContextDialog(SessionAwareDialog):
    def __init__(
        self, parent, alignment, dimensions, name="", caller=None, *args, **kwargs
    ):
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            "Delete Context",
            Common.color("modal_dialog_border_title"),
        )
        super().__init__(parent, alignment, dimensions, caller=caller, *args, **kwargs)
        self.name = name
        self.add_field(
            DialogFieldLabel(
                [
                    ('Delete context "', Common.color("modal_dialog_label")),
                    (name, Common.color("modal_dialog_label_highlight")),
                    ('"?', Common.color("modal_dialog_label")),
                ]
            )
        )
        self.highlighted = 1
        self.caller = caller

    def input(self, inkey):
        if inkey.is_sequence and inkey.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(inkey)

    def accept_and_close(self):
        Common.Configuration.delete_context(self.name)
        self.close()

    def close(self):
        if self.caller is not None:
            self.caller.reload_contexts()
        super().close()


class ImportContextDialog(SessionAwareDialog):
    def __init__(self, parent, alignment, dimensions, caller=None, *args, **kwargs):
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
        self.add_field(DialogFieldLabel("Enter AWS context details"))
        self.error_label = DialogFieldLabel(
            "", default_color=Common.color("modal_dialog_error")
        )
        self.add_field(self.error_label)
        self.add_field(DialogFieldLabel(""))
        self.name_field = DialogFieldText(
            "Name:",
            label_min=12,
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

    def input(self, inkey):
        if not self.accepts_inputs:
            return True
        if inkey.is_sequence and inkey.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(inkey)

    def accept_and_close(self):
        if self.name_field.text == "":
            self.error_label.text = "Name cannot be blank."
            return
        try:
            sts = Common.Session.service_provider.whoami(
                keys={"access": self.access_key, "secret": self.secret_key}
            )
        except exceptions.ClientError as e:
            self.error_label.text = "Key verification failed"
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
    def __init__(self, parent, alignment, dimensions, caller=None, *args, **kwargs):
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
        self.add_field(DialogFieldLabel("Enter AWS context details"))
        self.error_label = DialogFieldLabel(
            "", default_color=Common.color("modal_dialog_error")
        )
        self.add_field(self.error_label)
        self.add_field(DialogFieldLabel(""))
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

    def input(self, inkey):
        if not self.accepts_inputs:
            return True
        if inkey.is_sequence and inkey.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(inkey)

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
        except exceptions.ClientError as e:
            self.error_label.text = "Key verification failed"
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


class ContextList(ListControl):
    def __init__(self, parent, alignment, dimensions, *args, **kwargs):
        super().__init__(
            parent,
            alignment,
            dimensions,
            color=Common.color("context_list_generic", "generic"),
            selection_color=Common.color("context_list_selection", "selection"),
            title_color=Common.color("context_list_heading", "column_title"),
            *args,
            **kwargs,
        )
        self.hotkey_display = HotkeyDisplay(
            self.parent,
            TopRightAnchor(1, 0),
            Dimension("33%|50", 8),
            self,
            session=Common.Session,
            highlight_color=Common.color("hotkey_display_title"),
            generic_color=Common.color("hotkey_display_value"),
            tag="context",
        )
        self.add_hotkey("a", self.add_new_context, "Add new context")
        self.add_hotkey("d", self.set_default_context, "Set as default")
        self.add_hotkey("i", self.import_context, "Import context")
        self.add_hotkey("KEY_ENTER", self.select_context, "Select context")
        self.add_hotkey("\x04", self.delete_selected_context, "Delete context")
        self.new_context_dialog = None
        self.add_column("account id", 12)
        self.add_column("default", 7)
        idx = 0

        self.reload_contexts()

    def reload_contexts(self):
        self.entries = []
        self.selected = 0
        idx = 0
        defa = 0
        for context, data in Common.Configuration["contexts"].items():
            if context == Common.Configuration["default_context"]:
                defa = idx
                d = "✓"
            else:
                d = " "
            self.add_entry(
                ListEntry(context, **{"account id": data["account_id"], "default": d})
            )

            idx += 1
        if self.selected >= len(self.entries) or self.selected < 0:
            self.selected = defa

    def add_new_context(self, _):
        AddContextDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "20"),
            caller=self,
            weight=-500,
        )

    def import_context(self, _):
        ImportContextDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "20"),
            caller=self,
            weight=-500,
        )

    def set_default_context(self, _):
        if self.selection is not None:
            Common.Configuration["default_context"] = self.selection.name
            Common.Configuration.write_config()
            self.reload_contexts()

    def select_context(self, _):
        if self.selection is not None:
            Common.Session.context = self.selection.name

    def delete_selected_context(self, _):
        if self.selection is not None:
            DeleteContextDialog(
                self.parent,
                CenterAnchor(0, 0),
                Dimension("80%|40", 10),
                name=self.selection.name,
                caller=self,
                weight=-500,
            )
