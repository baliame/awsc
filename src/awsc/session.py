"""
Session manager module.
"""

import atexit
import datetime
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

import jq
from packaging import version

from .info import InfoDisplay, NeutralDialog
from .termui.alignment import BottomLeftAnchor, Dimension, TopLeftAnchor
from .termui.dialog import DialogFieldLabel
from .termui.ui import UI, ControlCodes
from .version import VERSION as current_version


class Session:
    """
    Session manager object. Manages what's visible on the screen. Also stores some information related to the current user session.

    Attributes
    ----------
    jqc : dict
        JQ cache. Stores compiled JQ objects keyed by JQ statement.
    ui : awsc.termui.ui.UI
        The main UI object of AWSC.
    config : awsc.config.config.Config
        The configuration object also stored in Common. We cannot import Common.
    context_update_hooks : list(callable)
        A list of hooks to run when the active context is updated.
    info_display : awsc.info.InfoDisplay
        The top left information display, which contains information about the active session.
    global_hotkey_tooltips : dict
        A dict of global hotkeys and associated tooltips.
    message_display : awsc.info.NeutralDialog
        The message display is a dialog on the backend which shows a flashed message to the user.
    _message_labels : list(awsc.termui.dialog.DialogFieldLabel)
        Label fields for each line of the message display.
    _context : str
        Current AWS context.
    _region : str
        Current AWS region.
    _ssh_key : str
        Current SSH key.
    stack : list
        A stack of stack frames.
    stack_frame : list
        The topmost stack frame. This frame is the one that is being displayed to the user.
    resource_main : awsc.termui.control.Control
        The main control of the stack frame. Usually the first element passed in a new frame.
    service_provider : awsc.aws.AWS
        The AWS connection provider.
    message_time : float
        The remaining amount of time for which a flashed message continues to be displayed.
    last_tick : time.time
        The timestamp when the last tick was executed, for deltatime purposes.
    filterer: awsc.commander.Filterer
        The filterer object that is open in the session, if there is one.
    commander: awsc.commander.Commander
        The commander object that is open in the session, if there is one.
    commander_options : dict(str, callable)
        A map of available commander options mapped to the callback for that command.
    control_registry : dict(str, callable)
        A map of available awsc control opener functions keyed by classname.
    common : awsc.common.Common
        Reference back to the common object.
    """

    def jq(self, stmt):
        """
        Creates a compiled JQ object, or fetches from cache if it exists.

        Parameters
        ----------
        stmt : str
            The JQ statement to compile.

        Returns
        -------
        jq._Program
            The compiled JQ statement.
        """
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
                "MFA",
                "SSH Key",
                "Default SSH username",
                "Session duration",
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
        self.common = common
        self._message_labels = [DialogFieldLabel(""), DialogFieldLabel("")]
        for elem in self._message_labels:
            self.message_display.add_field(elem)
        self._context = None
        self.context_is_valid = False
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

        self.process_check_interval = 0.1
        self.next_process_check = time.time()
        self.port_forwards = {}

        self.filterer = None
        self.commander = None
        self.commander_options = {}
        self.control_registry = {}
        atexit.register(self.cleanup_port_forwards)

        self.set_version_information()

    def set_version_information(self):
        """
        Updates the version information on the info display.
        """
        update_character = "↑"
        version_str = current_version
        latest_tag = version.parse(current_version)
        latest_stable = latest_tag
        current_tag = latest_tag
        try:
            with urllib.request.urlopen("https://pypi.org/pypi/awsc/json") as resp:
                if resp.status == 200:
                    package_info = resp.read()
                    package_info_json = json.loads(package_info)
                    for release in package_info_json["releases"].keys():
                        release_tag = version.parse(release)
                        if release_tag > latest_tag:
                            latest_tag = release_tag
                        if (
                            not release_tag.is_prerelease
                            and release_tag > latest_stable
                        ):
                            latest_stable = release_tag
                    if latest_tag != current_tag:
                        if latest_stable != current_tag:
                            version_str = f"{str(current_tag)} ({update_character}{str(latest_stable)}, {update_character}?{str(latest_tag)}"
                        else:
                            version_str = f"{str(current_tag)} ({update_character}?{str(latest_tag)}"
                    else:
                        version_str = str(current_tag)

            self.info_display["AWSC Version"] = version_str
        except urllib.error.URLError as error:
            self.common.log_exception(
                error, "Core", subcategory="Version Check", set_message=False
            )

    def set_message(self, text, color):
        """
        Flashes a message to the user.

        Parameters
        ----------
        text : str
            The text to show.
        color : awsc.termui.color.Color
            The color to use for the shown text.
        """
        max_lines = len(self._message_labels)
        lines = [""] * max_lines
        line_no = 0
        while len(text) > self.ui.width - 1:
            line = text[: self.ui.width - 1]
            lines[line_no] = line
            text = text[self.ui.width - 1 :]
            line_no += 1
            if line_no >= max_lines:
                break
        if line_no < max_lines:
            lines[line_no] = text
        for i in range(max_lines):
            self._message_labels[i].texts = [(lines[i], color)]
        self.message_time = min(len(text) / 10.0, 5.0)
        self.last_tick = time.time()
        self.ui.dirty = True

    def replace_frame(self, new_frame, drop_stack=True):
        """
        Removes the topmost stack frame, replacing it with a new frame.

        Parameters
        ----------
        new_frame : list
            The new frame to replace the topmost stack frame with.
        drop_stack : bool
            If set, drop the entire stack of frames while doing it.
        """

        for elem in self.stack_frame:
            elem.parent.remove_block(elem)
        if drop_stack:
            self.stack = []
        self.resource_main = new_frame[0]
        self.stack_frame = new_frame[:]
        self.ui.dirty = True
        for elem in self.stack_frame:
            if hasattr(elem, "on_become_frame"):
                elem.on_become_frame()

    def push_frame(self, new_frame):
        """
        Pushes a new frame to the stack, replacing the currently active frame for display.

        Calling push_frame, then pop_frame should return to the same state.

        Parameters
        ----------
        new_frame : list
            The new stack frame to add.
        """
            
        self.stack.append(self.stack_frame[:])
        self.replace_frame(new_frame, drop_stack=False)
        if hasattr(new_frame[0], "add_hotkey"):
            if "KEY_ESCAPE" not in new_frame[0].tooltips:
                new_frame[0].add_hotkey("KEY_ESCAPE", self.pop_frame, "Back")
        self.ui.dirty = True
        for elem in self.stack_frame:
            if hasattr(elem, "on_become_frame"):
                elem.on_become_frame()

    def pop_frame(
        self, *args
    ):  # pylint: disable=unused-argument # hotkey hooks will always be passed an extra argument
        """
        Pops the topmost frame of the stack. Calls on_close of each element of the popped stack frame. Replaces the stack frame with the
        next frame in the stack, if such a frame exists.
        """
        for elem in self.stack_frame:
            if hasattr(elem, "on_close"):
                elem.on_close()
        if len(self.stack) > 0:
            self.replace_frame(self.stack.pop(), drop_stack=False)
        for elem in self.stack_frame:
            elem.reparent()
        self.ui.dirty = True

    def extend_frame(self, control):
        """
        Adds an additional control to the current frame.

        Parameters
        ----------
        control : awsc.termui.control.Control
            The control to insert into the frame.
        """
        self.stack_frame.append(control)
        self.ui.dirty = True
        if hasattr(control, "on_become_frame"):
            control.on_become_frame()

    def remove_from_frame(self, control):
        """
        Removes a control from the current frame. Calls on_close of the removed control.

        Parameters
        ----------
        control : awsc.termui.control.Control
            The control to remove from the frame.
        """
        if hasattr(control, "on_close"):
            control.on_close()
        try:
            self.stack_frame.remove(control)
        except ValueError:
            for elem in reversed(self.stack):
                if control in elem:
                    elem.remove(control)
                    return
        self.ui.dirty = True

    def add_port_forward(self, proc, host, local_port, remote_port):
        key = f'{local_port}:{host}:{remote_port}'
        self.port_forwards[key] = {"proc": proc, "host": host, "local_port": local_port, "remote_port": remote_port}

    def terminate_port_forward(self, key):
        if key in self.port_forwards:
            pf = self.port_forwards[key]
            proc = pf['proc']
            proc.kill()
            message = f"Port forward process to {pf['host']}:{pf['remote_port']} on localhost:{pf['local_port']} has been terminated"
            self.common.log(
                message,
                "SSM tunnel terminated",
                "SSM",
                "info",
                subcategory="SSM Tunnel",
                resource=None,
                set_message=True,
            )
            del self.port_forwards[key]


    def cleanup_port_forwards(self):
        for key in {} | self.port_forwards:
            self.terminate_port_forward(key)

    def tick(self):
        """
        Ticker function. Called on every main loop cycle.
        """
        now = time.time()
        delta = now - self.last_tick
        self.last_tick += delta
        if self.message_time > 0:
            self.message_time -= delta
            if self.message_time <= 0:
                for label in self._message_labels:
                    label.texts = []
        if hasattr(self.resource_main, "auto_refresh"):
            self.resource_main.auto_refresh()
        if now > self.next_process_check:
            self.next_process_check = now + self.process_check_interval
            eject = []
            for k, pf in self.port_forwards.items():
                proc = pf['proc']
                retcode = proc.poll()
                if retcode is not None:
                    message = f"Port forward process to {pf['host']}:{pf['remote_port']} on localhost:{pf['local_port']} exited with code {retcode}"
                    self.common.log(
                        message,
                        "SSM tunnel exited",
                        "SSM",
                        "info",
                        subcategory="SSM Tunnel",
                        resource=None,
                        set_message=True,
                    )
                    eject.append(k)
            for k in eject:
                del self.port_forwards[k]
        auth = self.context_auth
        if auth is not None:
            try:
                del self.info_display.special_colors["Session duration"]
            except KeyError:
                pass
            if "expiry" in auth:
                expires_at = datetime.datetime.fromtimestamp(auth["expiry"])
                now = datetime.datetime.now()
                if expires_at > now:
                    delta = expires_at - now
                    hours = delta.seconds // 3600
                    minutes = (delta.seconds - (hours * 3600)) // 60
                    seconds = delta.seconds - (hours * 3600) - (minutes * 60)
                    self.info_display["Session duration"] = (
                        f"{hours:02}:{minutes:02}:{seconds:02}"
                    )
                else:
                    self.info_display.special_colors["Session duration"] = (
                        self.common.color("error")
                    )
                    self.info_display["Session duration"] = "Expired"
            else:
                if auth["access"] == "" or auth["secret"] == "":
                    self.info_display.special_colors["Session duration"] = (
                        self.common.color("error")
                    )
                    self.info_display["Session duration"] = "Expired"
                    return

                self.info_display["Session duration"] = "Permanent"

    @property
    def context(self):
        """
        Property. The currently active context.
        """
        return self._context

    @context.setter
    def context(self, value):
        if value == '' or value is None:
            self._context = None
            self.info_display["Context"] = "<No context>"
            self.context_is_valid = False
        else:
            self._context = value
            self.context_is_valid = True
            self.info_display["Context"] = value
            data = self.context_data
            auth = self.context_auth
            self.info_display["MFA"] = (
                "Disabled"
                if "mfa_device" not in data or data["mfa_device"] == ""
                else ("Authenticated" if "session" in auth else "Unauthenticated")
            )
            for elem in self.context_update_hooks:
                elem()

    def retrieve_context(self, name):
        """
        Returns the details of a specific context.

        Parameters
        ----------
        name : str
            The context for which details should be retrieved.

        Returns
        -------
        object
            An object with three keys.
            - The data key contains the non-sensitive context data.
              Equivalent to Session.context_data with the context as the active context.
            - The auth key contains the sensitive authentication context data.
              Equivalent to Session.context_auth with the context as the active context.
            - The perm key contains the sensitive permanent authentication context data.
              Equivalent to Session.context_perm_auth with the context as the active context.
        """
        return {
            "data": self.config.enumerated_contexts()[name],
            "auth": self.config.keystore[name],
            "perm": self.config.keystore.get_permanent_credentials(name),
        }

    @property
    def context_data(self):
        """
        Property. Directly accesses context data for convenience.
        """
        if self.context_is_valid:
            return self.config.enumerated_contexts()[self._context]
        return {}

    @property
    def context_auth(self):
        """
        Property. Directly accesses context keystore for convenience.
        """
        if self.context_is_valid:
            return self.config.keystore[self._context]
        return {}

    @property
    def context_perm_auth(self):
        """
        Property. Directly accesses context keystore for convenience.
        """
        if self.context_is_valid:
            return self.config.keystore.get_permanent_credentials(self._context)
        return {}

    @property
    def region(self):
        """
        Property. The current region.
        """
        return self._region

    @region.setter
    def region(self, value):
        self._region = value
        self.info_display["Region"] = value

    @property
    def ssh_key(self):
        """
        Property. The current ssh key.
        """
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

    @property
    def ephemeral(self):
        return self.common.Configuration.context_is_ephemeral(self.context)

    def get_keypair_association(self, keypair_id):
        """
        Fetches the keypair association of a keypair from the configuration.

        Parameters
        ----------
        keypair_id : str
            The ID of the keypair being queried.

        Returns
        -------
        str
            The SSH key the keypair is associated with.
        """
        if keypair_id in self.config["keypair_associations"]:
            return self.config["keypair_associations"][keypair_id]
        return ""

    def set_keypair_association(self, keypair_id, key_name):
        """
        Sets the association between a keypair and an SSH key.

        Parameters
        ----------
        keypair_id : str
            The ID of the keypair being associated.
        key_name : str
            The name of the SSH key associated with the keypair.
        """
        self.config["keypair_associations"][keypair_id] = key_name
        self.config.write_config()

    def textedit(self, value):
        """
        Open the text editor command specified in the editor_command configuration option to edit a text. Returns when the called command
        exits.

        Parameters
        ----------
        value : str
            The initial text to edit in the text editor.

        Returns
        -------
        str
            The edited text.
        """
        editor = self.config["editor_command"]
        with tempfile.NamedTemporaryFile("w", delete=False) as temp:
            temp_file = temp.name
            temp.write(value)
            temp.close()
        try:
            self.ui.unraw(subprocess.run, ["bash", "-c", editor.format(temp_file)])
            with open(temp_file, "r", encoding="utf-8") as temp:
                return temp.read()
        finally:
            os.unlink(temp.name)

    def get_default_dashboard_layout(self):
        """
        Returns the default configured dashboard layout.

        Returns
        -------
        list(list(str))
            A list of rows of dashboard block class names.
        """
        if "default_dashboard_layout" in self.config:
            return self.config["default_dashboard_layout"]
        return [["Blank", "Blank"], ["Blank", "Blank"]]

    def get_context_dashboard_layout(self):
        """
        Returns the configured dashboard layout for the currently selected context.

        Returns
        -------
        list(list(str))
            A list of rows of dashboard block class names.
        """
        if self.context in self.config["dashboard_layouts"]:
            return self.config["dashboard_layouts"][self.context]
        return self.get_default_dashboard_layout()
