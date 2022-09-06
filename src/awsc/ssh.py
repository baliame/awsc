"""
Controls related to SSH keys.
"""
import re
from pathlib import Path

from .base_control import OpenableListControl
from .common import Common
from .termui.alignment import CenterAnchor, Dimension
from .termui.control import Border
from .termui.dialog import DialogControl, DialogFieldText
from .termui.list_control import ListEntry


# TODO: Implement usage frequency.
class SSHList(OpenableListControl):
    """
    Lister control for available SSH keys.
    """

    prefix = "ssh"
    title = "SSH Keys"

    def __init__(self, *args, selector_cb=None, **kwargs):
        super().__init__(
            *args,
            color=Common.color("ssh_key_list_generic", "generic"),
            selection_color=Common.color("ssh_key_list_selection", "selection"),
            title_color=Common.color("ssh_key_list_heading", "column_title"),
            selector_cb=selector_cb,
            **kwargs,
        )

        if selector_cb is None:
            self.add_hotkey("KEY_ENTER", self.select_ssh_key, "Select ssh key")
        self.add_column("usage frequency", 12)
        self.add_column("has public key", 12)
        self.add_column("default username", 20)
        self.add_column("default", 8)
        self.reload()

    def reload(self, move=True):
        """
        Reloads the list of available SSH keys.

        Parameters
        ----------
        move : bool
            If True, moves the selection cursor to the default SSH key.
        """
        self.entries = []
        idx = 0
        defa = 0
        for ssh_key in sorted(self.list_ssh_keys()):
            if ssh_key == Common.Configuration["default_ssh_key"]:
                defa = idx
                is_default = "✓"
            else:
                is_default = " "
            pubkey = Path.home() / ".ssh" / f"{ssh_key}.pub"
            has_pubkey = "✓" if pubkey.exists() else " "
            default_username = (
                Common.Configuration["default_ssh_usernames"][ssh_key]
                if ssh_key in Common.Configuration["default_ssh_usernames"]
                else ""
            )
            self.add_entry(
                ListEntry(
                    ssh_key,
                    **{
                        "usage frequency": 0,
                        "has public key": has_pubkey,
                        "default username": default_username,
                        "default": is_default,
                    },
                )
            )
            idx += 1
        if move:
            self.selected = defa

    def list_ssh_keys(self):
        """
        Fetches a list of available SSH keys from ~/.ssh. Only files beginning with `id_` or with the .pem extension are used.

        Returns
        -------
        list(str)
            A list of filenames in ~/.ssh matching the pattern.
        """
        ssh_dir = Path.home() / ".ssh"
        ret = []
        for child in ssh_dir.iterdir():
            filename = child.name
            if re.match(r"^((id_[^.]+?)|(.*?\.pem))$", filename) is not None:
                ret.append(filename)
        return ret

    @OpenableListControl.Autohotkey("d", "Set as default", True)
    def set_default_ssh_key(self, _):
        """
        Hotkey callback for setting the default SSH key.
        """
        if self.selection is not None:
            Common.Configuration["default_ssh_key"] = self.selection.name
            Common.Configuration.write_config()
            for entry in self.entries:
                if entry.name != Common.Configuration["default_ssh_key"]:
                    entry["default"] = " "
                else:
                    entry["default"] = "✓"

    def select_ssh_key(self, _):
        """
        Hotkey callback for setting the active SSH key.
        """
        if self.selection is not None:
            Common.Session.ssh_key = self.selection.name

    @OpenableListControl.Autohotkey("e", "Set default username", True)
    def set_default_ssh_username(self, _):
        """
        Hotkey callback for associating a default username with an SSH key.
        """
        SSHDefaultUsernameDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            key_name=self.selection["name"],
            caller=self,
            weight=-500,
        )


# TODO: Replace with SingleNameDialog?
class SSHDefaultUsernameDialog(DialogControl):
    """
    Dialog for entering the default username for an SSH key.

    Attributes
    ----------
    username_textfield : awsc.termui.dialog.DialogFieldText
        Textfield for entering the default username.
    caller : awsc.termui.control.Control
        The parent control controlling this dialog.
    key_name : str
        The SSH key to associate the username with.
    """

    def __init__(self, *args, key_name="", caller=None, **kwargs):
        self.key_name = key_name
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        kwargs["border"] = Border(
            Common.border("ssh", "default"),
            Common.color("ssh_modal_dialog_border", "modal_dialog_border"),
            "Default SSH username",
            Common.color("ssh_modal_dialog_border_title", "modal_dialog_border_title"),
            self.key_name,
            Common.color(
                "ssh_modal_dialog_border_title_info", "modal_dialog_border_title_info"
            ),
        )
        super().__init__(*args, **kwargs)
        def_text = (
            Common.Configuration["default_ssh_usernames"][self.key_name]
            if self.key_name in Common.Configuration["default_ssh_usernames"]
            else ""
        )
        self.username_textfield = DialogFieldText(
            "SSH username",
            text=def_text,
            **Common.textfield_colors("ec2_ssh"),
        )
        self.add_field(self.username_textfield)
        self.highlighted = 1 if def_text != "" else 0
        self.caller = caller

    def input(self, key):
        if key.is_sequence and key.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(key)

    def accept_and_close(self):
        """
        Affirmative action callback. Sets the ssh key default username.
        """
        Common.Configuration["default_ssh_usernames"][
            self.key_name
        ] = self.username_textfield.text
        Common.Configuration.write_config()
        Common.Session.ssh_key = Common.Session.ssh_key  # don't ask
        self.caller.reload(move=False)
        self.close()

    def close(self):
        """
        Negative action callback. Closes the dialog.
        """
        self.parent.remove_block(self)
