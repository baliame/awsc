import json
from .base_control import DeleteResourceDialog, GenericDescriber, OpenableListControl
from .common import Common, datetime_hack
from .termui.list_control import ListEntry
from .termui.ui import ControlCodes


class PortForwardDescriber(GenericDescriber):
    def __init__(self, *args, selection, **kwargs):
        data = {} | Common.Session.port_forwards[selection['name']]
        del data['proc']
        content = json.dumps(data, default=datetime_hack, indent=2, sort_keys=True)
        super().__init__(
            *args,
            describing="port forward",
            content=content,
            **kwargs,
        )


class PortForwardList(OpenableListControl):
    """
    Lister control for port forwards.
    """

    prefix = "port_forward_list"
    title = "Port forwards"
    describer = PortForwardDescriber.opener

    auto_refresh_interval = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hide_name_column()
        self.add_column("host", 50)
        self.add_column("local port", 5)
        self.add_column("remote port", 5)
        
        self.auto_refresher = self.reload_port_forwards
        self.reload_port_forwards()

    def reload_port_forwards(self):
        """
        Refreshes the list of contexts from configuration.
        """
        self.entries = []
        for name, pf in Common.Session.port_forwards.items():
            self.add_entry(ListEntry(name, **{"host": pf['host'], "local port": pf['local_port'], "remote port": pf['remote_port']}))
        self._cache = None
        Common.Session.ui.dirty = True

    def on_become_frame(self):
        super().on_become_frame()
        self.on_become_frame_hooks.clear()

    @OpenableListControl.Autohotkey(ControlCodes.D, "Terminate port forward", True)
    def terminate_port_forward(self, _):
        """
        Hotkey callback for terminating the selected port forward.
        """
        DeleteResourceDialog.opener(
            caller=self,
            resource_type="port forward",
            action="Terminate",
            resource_identifier=self.selection["name"],
            callback=self.do_terminate,
        )

    def do_terminate(self, **kwargs):
        """
        Action callback for the port forward termination dialog.
        """
        Common.Session.terminate_port_forward(self.selection['name'])
        self.reload_port_forwards()

        