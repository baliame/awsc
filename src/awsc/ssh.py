import re
from pathlib import Path

from .common import Common, DefaultAnchor, DefaultBorder, DefaultDimension
from .info import HotkeyDisplay
from .termui.alignment import CenterAnchor, Dimension, TopRightAnchor
from .termui.control import Border
from .termui.dialog import DialogControl, DialogFieldText
from .termui.list_control import ListControl, ListEntry


class SSHList(ListControl):
    @classmethod
    def opener(cls, **kwargs):
        l = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            **kwargs,
        )
        l.border = DefaultBorder("ssh", "SSH Keys", None)
        return [l, l.hotkey_display]

    @classmethod
    def selector(cls, cb, **kwargs):
        return cls.opener(**{"selector_cb": cb, **kwargs})

    def __init__(
        self, parent, alignment, dimensions, selector_cb=None, *args, **kwargs
    ):
        super().__init__(
            parent,
            alignment,
            dimensions,
            color=Common.color("ssh_key_list_generic", "generic"),
            selection_color=Common.color("ssh_key_list_selection", "selection"),
            title_color=Common.color("ssh_key_list_heading", "column_title"),
            *args,
            **kwargs,
        )
        self.selector_cb = selector_cb
        self.hotkey_display = HotkeyDisplay(
            self.parent,
            TopRightAnchor(1, 0),
            Dimension("33%|50", 8),
            self,
            session=Common.Session,
            highlight_color=Common.color("hotkey_display_title"),
            generic_color=Common.color("hotkey_display_value"),
        )
        self.add_hotkey("d", self.set_default_ssh_key, "Set as default")
        self.add_hotkey("e", self.set_default_ssh_username, "Set default username")
        if selector_cb is not None:
            self.add_hotkey("KEY_ENTER", self.select_and_close, "Select and close")
        else:
            self.add_hotkey("KEY_ENTER", self.select_ssh_key, "Select ssh key")
        self.add_column("usage frequency", 12)
        self.add_column("has public key", 12)
        self.add_column("default username", 20)
        self.add_column("default", 8)
        self.reload()

    def reload(self, move=True):
        self.entries = []
        idx = 0
        defa = 0
        for ssh_key in sorted(self.list_ssh_keys()):
            if ssh_key == Common.Configuration["default_ssh_key"]:
                defa = idx
                d = "✓"
            else:
                d = " "
            pubkey = Path.home() / ".ssh" / "{0}.pub".format(ssh_key)
            has_pubkey = "✓" if pubkey.exists() else " "
            du = (
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
                        "default username": du,
                        "default": d,
                    },
                )
            )
            idx += 1
        if move:
            self.selected = defa

    def list_ssh_keys(self):
        ssh_dir = Path.home() / ".ssh"
        ret = []
        for child in ssh_dir.iterdir():
            fn = child.name
            if re.match(r"^((id_[^.]+?)|(.*?\.pem))$", fn) is not None:
                ret.append(fn)
        return ret

    def set_default_ssh_key(self, _):
        if self.selection is not None:
            Common.Configuration["default_ssh_key"] = self.selection.name
            Common.Configuration.write_config()
            for entry in self.entries:
                if entry.name != Common.Configuration["default_ssh_key"]:
                    entry.columns["default"] = " "
                else:
                    entry.columns["default"] = "✓"

    def select_ssh_key(self, _):
        if self.selection is not None:
            Common.Session.ssh_key = self.selection.name

    def select_and_close(self, _):
        if self.selection is not None and self.selector_cb is not None:
            self.selector_cb(self.selection["name"])
            Common.Session.pop_frame()

    def set_default_ssh_username(self, _):
        SSHDefaultUsernameDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            key_name=self.selection["name"],
            caller=self,
            weight=-500,
        )


class SSHDefaultUsernameDialog(DialogControl):
    def __init__(
        self, parent, alignment, dimensions, key_name="", caller=None, *args, **kwargs
    ):
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
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        def_text = (
            Common.Configuration["default_ssh_usernames"][self.key_name]
            if self.key_name in Common.Configuration["default_ssh_usernames"]
            else ""
        )
        self.username_textfield = DialogFieldText(
            "SSH username",
            text=def_text,
            color=Common.color(
                "ec2_ssh_modal_dialog_textfield", "modal_dialog_textfield"
            ),
            selected_color=Common.color(
                "ec2_ssh_modal_dialog_textfield_selected",
                "modal_dialog_textfield_selected",
            ),
            label_color=Common.color(
                "ec2_ssh_modal_dialog_textfield_label", "modal_dialog_textfield_label"
            ),
            label_min=16,
        )
        self.add_field(self.username_textfield)
        self.highlighted = 1 if def_text != "" else 0
        self.caller = caller

    def input(self, inkey):
        if inkey.is_sequence and inkey.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(inkey)

    def accept_and_close(self):
        Common.Configuration["default_ssh_usernames"][
            self.key_name
        ] = self.username_textfield.text
        Common.Configuration.write_config()
        Common.Session.ssh_key = Common.Session.ssh_key  # don't ask
        self.caller.reload(move=False)
        self.close()

    def close(self):
        self.parent.remove_block(self)
