import json
import os
import subprocess
import tempfile
import time
import urllib.request

import jq
from packaging import version

from .info import InfoDisplay, NeutralDialog
from .termui.alignment import BottomLeftAnchor, Dimension, TopLeftAnchor
from .termui.dialog import DialogFieldLabel
from .termui.ui import UI, ControlCodes
from .version import version as current_version


class Session:
    def jq(self, stmt):
        if stmt not in self.jqc:
            self.jqc[stmt] = jq.compile(stmt)
        return self.jqc[stmt]

    def __init__(self, config, highlight_color, generic_color, common):
        self.jqc = {}
        self.ui = UI()
        self.config = config
        self.context_update_hooks = []
        self.info_display = InfoDisplay(
            self.ui.top_block,
            TopLeftAnchor(1, 0),
            Dimension("50%", 8),
            highlight_color=highlight_color,
            generic_color=generic_color,
            info=[
                "AWSC Version",
                "Context",
                "Region",
                "UserId",
                "Account",
                "SSH Key",
                "Default SSH username",
            ],
            weight=-10,
        )
        self.global_hotkey_tooltips = {
            ":": "Command palette",
            "/": "Filter / search",
            ControlCodes.C: "Exit",
        }
        self.message_display = NeutralDialog(
            self.ui.top_block,
            BottomLeftAnchor(0, 0),
            Dimension("100%", 3),
            confirm_text=None,
            cancel_text=None,
            color=generic_color,
            weight=-10,
        )
        self._message_label = DialogFieldLabel("")
        self._message_label_l2 = DialogFieldLabel("")
        self.message_display.add_field(self._message_label)
        self.message_display.add_field(self._message_label_l2)
        self._context = None
        self.context = config["default_context"]
        self.region = config["default_region"]
        self.ssh_key = config["default_ssh_key"]
        self.stack = []
        self.stack_frame = []
        self.resource_main = None
        self.service_provider = None
        self.message_time = 0
        self.last_tick = time.time()
        self.ui.tickers.append(self.tick)

        self.filterer = None
        self.commander = None
        self.commander_options = {}
        self.common = common

        self.set_version_information()

    def set_version_information(self):
        update_character = "↑"
        version_str = current_version
        latest_tag = version.parse(current_version)
        latest_stable = latest_tag
        current_tag = latest_tag
        resp = urllib.request.urlopen("https://pypi.org/pypi/awsc/json")
        if resp.status == 200:
            package_info = resp.read()
            package_info_json = json.loads(package_info)
            for release in package_info_json["releases"].keys():
                release_tag = version.parse(release)
                if release_tag > latest_tag:
                    latest_tag = release_tag
                if not release_tag.is_prerelease and release_tag > latest_stable:
                    latest_stable = release_tag
            if latest_tag != current_tag:
                if latest_stable != current_tag:
                    version_str = "{current} ({update_character}{stable}, {update_character}?{development}".format(
                        current=str(current_tag),
                        stable=str(latest_stable),
                        development=str(latest_tag),
                        update_character=update_character,
                    )
                else:
                    version_str = "{current} ({update_character}?{development}".format(
                        current=str(current_tag),
                        development=str(latest_tag),
                        update_character=update_character,
                    )
            else:
                version_str = str(current_tag)

        self.info_display["AWSC Version"] = version_str

    def set_message(self, text, color):
        l1 = text
        l2 = ""
        if len(text) > self.ui.w:
            l1 = text[: self.ui.w]
            l2 = text[self.ui.w :]
            if len(l2) > self.ui.w:
                l2 = l2[: self.ui.w]
        self._message_label.texts = [(l1, color)]
        self._message_label_l2.texts = [(l2, color)]
        self.message_time = min(len(text) / 10.0, 5.0)
        self.last_tick = time.time()
        self.ui.dirty = True

    def replace_frame(self, new_frame, drop_stack=True):
        for elem in self.stack_frame:
            elem.parent.remove_block(elem)
        if drop_stack:
            self.stack = []
        self.resource_main = new_frame[0]
        self.stack_frame = new_frame[:]
        self.ui.dirty = True

    def push_frame(self, new_frame):
        self.stack.append(self.stack_frame[:])
        self.replace_frame(new_frame, drop_stack=False)
        if hasattr(new_frame[0], "add_hotkey"):
            if "KEY_ESCAPE" not in new_frame[0].tooltips:
                new_frame[0].add_hotkey("KEY_ESCAPE", self.pop_frame, "Back")
        self.ui.dirty = True

    def pop_frame(
        self, *args
    ):  # pylint: disable=unused-argument # hotkey hooks will always be passed an extra argument
        for elem in self.stack_frame:
            if hasattr(elem, "on_close"):
                elem.on_close()
        if len(self.stack) > 0:
            self.replace_frame(self.stack.pop(), drop_stack=False)
        for elem in self.stack_frame:
            elem.reparent()
        self.ui.dirty = True

    def extend_frame(self, control):
        self.stack_frame.append(control)
        self.ui.dirty = True

    def remove_from_frame(self, control):
        if hasattr(control, "on_close"):
            control.on_close()
        try:
            self.stack_frame.remove(control)
        except ValueError as e:
            for elem in reversed(self.stack):
                if control in elem:
                    elem.remove(control)
                    return
        self.ui.dirty = True

    def tick(self):
        delta = time.time() - self.last_tick
        self.last_tick += delta
        if self.message_time > 0:
            self.message_time -= delta
            if self.message_time <= 0:
                self._message_label.texts = []
                self._message_label_l2.texts = []
        if hasattr(self.resource_main, "auto_refresh"):
            self.resource_main.auto_refresh()

    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, value):
        if self._context == value:
            return
        self._context = value
        self.info_display["Context"] = value
        for elem in self.context_update_hooks:
            elem()

    @property
    def region(self):
        return self._region

    @region.setter
    def region(self, value):
        self._region = value
        self.info_display["Region"] = value

    @property
    def ssh_key(self):
        return self._ssh_key

    @ssh_key.setter
    def ssh_key(self, value):
        self._ssh_key = value
        self.info_display["SSH Key"] = value
        self.info_display["Default SSH username"] = (
            self.config["default_ssh_usernames"][value]
            if value in self.config["default_ssh_usernames"]
            else ""
        )

    def get_keypair_association(self, keypair_id):
        if keypair_id in self.config["keypair_associations"]:
            return self.config["keypair_associations"][keypair_id]
        return ""

    def set_keypair_association(self, keypair_id, key_name):
        self.config["keypair_associations"][keypair_id] = key_name
        self.config.write_config()

    def textedit(self, value):
        editor = self.config["editor_command"]
        temp = tempfile.NamedTemporaryFile("w", delete=False)
        tf = temp.name
        try:
            temp.write(value)
            temp.close()
            self.ui.unraw(subprocess.run, ["bash", "-c", editor.format(tf)])
            with open(tf, "r") as temp:
                return temp.read()
        finally:
            os.unlink(temp.name)
