from pathlib import Path

from .base_control import Describer, ResourceLister
from .common import Common, SessionAwareDialog
from .ssh import SSHList
from .termui.control import Border
from .termui.dialog import DialogFieldLabel, DialogFieldText


class KeyPairResourceLister(ResourceLister):
    prefix = "keypair_list"
    title = "EC2 Keypairs"
    command_palette = ["key", "keypair"]

    def __init__(self, *args, **kwargs):
        self.resource_key = "ec2"
        self.list_method = "describe_key_pairs"
        self.item_path = ".KeyPairs"
        self.column_paths = {
            "id": ".KeyPairId",
            "name": ".KeyName",
            "fingerprint": ".KeyFingerprint",
            "association": self.determine_keypair_association,
        }
        self.imported_column_sizes = {
            "id": 16,
            "name": 32,
            "fingerprint": 48,
            "association": 16,
        }
        self.describe_command = KeyPairDescriber.opener
        self.imported_column_order = ["id", "name", "fingerprint", "association"]
        self.primary_key = "id"
        self.sort_column = "id"
        super().__init__(*args, **kwargs)
        self.add_hotkey("a", self.set_keypair_association, "Associate with SSH key")
        self.add_hotkey("c", self.create_keypair, "Create new keypair")
        self.add_hotkey("x", self.remove_keypair_association, "Remove association")

    def determine_keypair_association(self, entry):
        return Common.Session.get_keypair_association(entry["KeyPairId"])

    def set_keypair_association(self, _):
        if self.selection is not None:
            Common.Session.push_frame(SSHList.selector(self.ssh_selector_callback))
            Common.Session.ui.dirty = True

    def ssh_selector_callback(self, val):
        if self.selection is not None:
            Common.Session.set_keypair_association(self.selection["id"], val)
            self.refresh_data()

    def create_keypair(self, _):
        KeyPairCreateDialog.opener(self)

    def remove_keypair_association(self, _):
        if self.selection is not None:
            Common.Session.set_keypair_association(self.selection["id"], "")
            self.refresh_data()


class KeyPairCreateDialog(SessionAwareDialog):
    def __init__(self, *args, caller=None, **kwargs):
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            "Create new keypair",
            Common.color("modal_dialog_border_title"),
        )
        super().__init__(*args, caller=caller, **kwargs)
        self.add_field(DialogFieldLabel("Enter keypair details"))
        self.error_label = DialogFieldLabel(
            "", default_color=Common.color("modal_dialog_error")
        )
        self.add_field(self.error_label)
        self.name_field = DialogFieldText(
            "Name:",
            label_min=16,
            color=Common.color("modal_dialog_textfield"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
            label_color=Common.color("modal_dialog_textfield_label"),
        )
        self.add_field(self.name_field)
        self.dotssh = Path.home() / ".ssh"
        self.add_field(
            DialogFieldLabel(
                "Key file will be saved in {0}".format(str(self.dotssh.resolve()))
            )
        )
        self.save_as_field = DialogFieldText(
            "Filename:",
            label_min=16,
            color=Common.color("modal_dialog_textfield"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
            label_color=Common.color("modal_dialog_textfield_label"),
        )
        self.add_field(self.save_as_field)
        self.caller = caller

    def accept_and_close(self):
        if self.name_field.text == "":
            self.error_label.text = "Name cannot be blank."
            return
        if self.save_as_field.text == "":
            self.error_label.text = "Filename cannot be blank."
            return
        if "/" in self.save_as_field.text or "\\" in self.save_as_field.text:
            self.error_label.text = "Filename cannot contain path separators."
            return

        resps = Common.generic_api_call(
            "ec2",
            "create_key_pair",
            {"KeyName": self.name_field.text},
            "Create Keypair",
            "EC2",
            subcategory="Key Pair",
            success_template="Creating keypair {0}",
            resource=self.name_field.text,
        )
        if resps["Success"]:
            resp = resps["Response"]
            data = resp["KeyMaterial"]
            with (self.dotssh / self.save_as_field.text).open("w") as f:
                f.write(data)
            Common.Session.set_keypair_association(
                resp["KeyPairId"], self.save_as_field.text
            )

        super().accept_and_close()

    def close(self):
        if self.caller is not None:
            self.caller.refresh_data()
        super().close()


class KeyPairDescriber(Describer):
    prefix = "keypair_browser"
    title = "EC2 Keypair"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="id", **kwargs
    ):
        self.resource_key = "ec2"
        self.describe_method = "describe_key_pairs"
        self.describe_kwarg_name = "KeyPairIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".KeyPairs[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
