"""
Module for keypair resources.
"""
from pathlib import Path

from .base_control import Describer, ResourceLister
from .common import Common, SessionAwareDialog
from .ssh import SSHList
from .termui.control import Border
from .termui.dialog import DialogFieldLabel, DialogFieldText


class KeyPairDescriber(Describer):
    """
    Describer control for keypairs.
    """

    prefix = "keypair_browser"
    title = "EC2 Keypair"

    def __init__(self, *args, entry_key="id", **kwargs):
        self.resource_key = "ec2"
        self.describe_method = "describe_key_pairs"
        self.describe_kwarg_name = "KeyPairIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".KeyPairs[0]"
        super().__init__(*args, entry_key=entry_key, **kwargs)


def _keypair_determine_association(entry):
    return Common.Session.get_keypair_association(entry["KeyPairId"])


class KeyPairResourceLister(ResourceLister):
    """
    Lister control for keypairs.
    """

    prefix = "keypair_list"
    title = "EC2 Keypairs"
    command_palette = ["key", "keypair"]

    resource_type = "keypair"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "Keypair"
    list_method = "describe_key_pairs"
    item_path = ".KeyPairs"
    columns = {
        "id": {
            "path": ".KeyPairId",
            "size": 16,
            "weight": 0,
        },
        "name": {"path": ".KeyName", "size": 32, "weight": 1, "sort_weight": 0},
        "fingerprint": {
            "path": ".KeyFingerprint",
            "size": 48,
            "weight": 2,
        },
        "association": {
            "path": _keypair_determine_association,
            "size": 16,
            "weight": 3,
        },
    }
    primary_key = "id"
    describe_command = KeyPairDescriber.opener

    @ResourceLister.Autohotkey("a", "Associate with SSH key", True)
    def set_keypair_association(self, _):
        """
        Hotkey callback for setting keypair association.
        """
        Common.Session.push_frame(SSHList.selector(self.ssh_selector_callback))
        Common.Session.ui.dirty = True

    def ssh_selector_callback(self, val):
        """
        Selector callback for keypair association.
        """
        Common.Session.set_keypair_association(self.selection["id"], val)
        self.refresh_data()

    @ResourceLister.Autohotkey("n", "New keypair")
    def create_keypair(self, _):
        """
        Hotkey callback for creating a new keypair.
        """
        KeyPairCreateDialog.opener(self, caller=self)

    @ResourceLister.Autohotkey("x", "Remove association", True)
    def remove_keypair_association(self, _):
        """
        Hotkey callback for deleting keypair association.
        """
        Common.Session.set_keypair_association(self.selection["id"], "")
        self.refresh_data()


class KeyPairCreateDialog(SessionAwareDialog):
    """
    Dialog for creating a keypair.

    Attributes
    ----------
    name_field : awsc.termui.dialog.DialogFieldText
        The textfield for entering a name.
    error_label : awsc.termui.dialog.DialogFieldLabel
        A label where error feedback may be dispalyed.
    dotssh : pathlib.Path
        The path to ~/.ssh
    save_as_field : awsc.termui.dialog.DialogFieldText
        The name of the output file for the downloaded SSH key.
    """

    def __init__(self, *args, caller=None, **kwargs):
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            "Create new keypair",
            Common.color("modal_dialog_border_title"),
        )
        super().__init__(*args, caller=caller, **kwargs)
        self.set_title_label("Enter keypair details")
        self.name_field = DialogFieldText(
            "Name:",
            **Common.textfield_colors("ec2_keypair"),
        )
        self.add_field(self.name_field)
        self.dotssh = Path.home() / ".ssh"
        self.add_field(
            DialogFieldLabel(f"Key file will be saved in {str(self.dotssh.resolve())}")
        )
        self.save_as_field = DialogFieldText(
            "Filename:",
            **Common.textfield_colors("ec2_keypair"),
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
            with (self.dotssh / self.save_as_field.text).open("w") as file:
                file.write(data)
            Common.Session.set_keypair_association(
                resp["KeyPairId"], self.save_as_field.text
            )

        super().accept_and_close()

    def close(self):
        if self.caller is not None:
            self.caller.refresh_data()
        super().close()
