"""
Module for common storage and functions.
"""
import configparser
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Set

import yaml
from botocore import exceptions

from .config.config import Config
from .session import Session
from .termui.alignment import CenterAnchor, Dimension, TopLeftAnchor
from .termui.bar_graph import BarGraph
from .termui.color import Color, Palette8Bit
from .termui.control import Border, BorderStyle
from .termui.dialog import DialogControl, DialogFieldLabel

DefaultAnchor = TopLeftAnchor(0, 11)
DefaultDimension = Dimension("100%", "100%-14")


def datetime_hack(x):
    """
    JSON dumper hack, as the base implementation of datetime doesn't understand how to convert it to JSON.

    Parameters
    ----------
    x : object
        The object the JSON dumper could not handle.

    Returns
    -------
    str
        The ISO representation of the datetime object.

    Raises
    ------
    TypeError
        If x is not a datetime.datetime object.
    """
    if isinstance(x, datetime):
        return x.isoformat()
    raise TypeError("Unknown type")


# TODO: Should be in base_control.
class BaseChart(BarGraph):
    """
    Base class for chart controls.
    """

    prefix = "CHANGEME"
    title = "CHANGEME"

    @classmethod
    def opener(cls, *args, **kwargs):
        """
        Session-aware initializer for this class. Creates a BaseChart object with the default alignment settings for the awsc layout.

        Returns
        -------
        list(awsc.common.BaseChart)
            A new instance of this class.
        """
        ret = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            *args,
            weight=0,
            color=Common.color("generic"),
            **kwargs,
        )
        ret.border = default_border(cls.prefix, cls.title, ret.title_info())
        return [ret]

    def title_info(self):
        """
        Title information callback.

        Returns
        -------
        str
            The extra info to display in the title.
        """
        return None


# TODO: Should be in base_control or separate dialog module.
class SessionAwareDialog(DialogControl):
    """
    Base class for dialogs.
    """

    line_size = 10

    @classmethod
    def opener(cls, *args, caller, **kwargs):
        """
        Session-aware initializer for this class. Creates a SessionAwareDialog object with the default alignment settings for the awsc layout.

        Returns
        -------
        awsc.common.SessionAwareDialog
            A new instance of this class.
        """
        return cls(
            caller.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", f"{cls.line_size}"),
            *args,
            caller=caller,
            weight=-500,
            **kwargs,
        )

    def __init__(self, *args, caller, **kwargs):
        caller.dialog_mode = True
        self.caller = caller
        Common.Session.extend_frame(self)
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        super().__init__(*args, **kwargs)
        self.title_label = DialogFieldLabel("TITLE")
        self.add_field(self.title_label)
        self.add_field(DialogFieldLabel(""))

        self.error_label = DialogFieldLabel(
            "", default_color=Common.color("modal_dialog_error")
        )
        self.add_field(self.error_label)
        self.add_field(DialogFieldLabel(""))

    def set_title_label(self, text):
        """
        Sets the text on the title label.

        Parameters
        ----------
        text : str
            The new title.
        """
        self.title_label.text = text

    def input(self, key):
        if key.is_sequence and key.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(key)

    def accept_and_close(self):
        """
        Callback for the affirmative action of the dialog. This should handle the data entered in the dialog, then execute the negative action.
        """
        self.close()

    def close(self):
        """
        Callback for the negative action of the dialog. This should _not_ handle the data entered in the dialog.
        """
        self.caller.dialog_mode = False
        self.parent.remove_block(self)
        Common.Session.remove_from_frame(self)


class Common:
    """
    Namespace class for common features used by awsc.

    Attributes
    ----------
    Configuration : awsc.config.config.Config
        The AWSC configuration.
    Session : awsc.session.Session
        The session manager object.
    _logholder : awsc.common.LogHolder
        The log stash object.
    initialized : bool
        Whether Common was initialized.
    init_hooks : set(callable)
        A set of hooks to execute after initialization.
    """

    Configuration: Config = Config()
    Session = None
    _logholder = None
    initialized = False
    init_hooks: Set[Callable[[], None]] = set()

    @classmethod
    def run_on_init(cls, hook):
        """
        Register a hook to run on initialization.

        Runs the hook immediately if already initialized.

        Parameters
        ----------
        hook : callable
            The hook to register.
        """
        if cls.initialized:
            hook()
        else:
            cls.init_hooks.add(hook)

    @classmethod
    def initialize(cls):
        """
        Initialize Common.
        """
        if cls.initialized:
            return
        cls.Configuration.initialize()
        cls.Session = Session(
            cls.Configuration,
            cls.color("info_display_title"),
            cls.color("info_display_value"),
            cls,
        )
        cls._logholder = LogHolder()
        cls.initialized = True

    @classmethod
    def post_initialize(cls):
        """
        Post-initialization actions for Common. Should be invoked from the outside, after initializing.
        """
        for hook in cls.init_hooks:
            hook()
        cls.load_dot_aws()

    @classmethod
    def load_dot_aws(cls):
        """
        Parse and load the contents of ~/.awsc/credentials. Adds contexts registered in that file as awsc contexts.
        """
        aws_creds = Path.home() / ".aws" / "credentials"
        print("Loading ~/.aws/credentials", file=sys.stderr)
        try:
            with aws_creds.open("r", encoding="utf-8") as file:
                creds = file.read()
        except OSError as error:
            print(
                f"Failed to open ~/.aws/credentials: {str(error)}",
                file=sys.stderr,
            )
            return
        parser = configparser.ConfigParser(default_section="__default")
        parser.read_string(creds)
        for section in parser.sections():
            if "aws_access_key_id" not in parser[section]:
                print(
                    f"aws_access_key_id missing for credential {section}, skipping",
                    file=sys.stderr,
                )
                continue
            if "aws_secret_access_key" not in parser[section]:
                print(
                    f"aws_secret_access_key missing for credential {section}, skipping",
                    file=sys.stderr,
                )
                continue
            access = parser[section]["aws_access_key_id"]
            secret = parser[section]["aws_secret_access_key"]
            api_keypair = {"access": access, "secret": secret}
            try:
                whoami = cls.Session.service_provider.whoami(keys=api_keypair)
            except exceptions.ClientError as error:
                cls.clienterror(
                    error,
                    "Verify Credentials",
                    "Bootstrap",
                    subcategory="Credentials Import",
                    resource=section,
                    set_message=False,
                    api_provider="sts",
                    api_method="get_caller_identity",
                    api_keypair=api_keypair,
                    api_args={},
                    credentials_section=section,
                )
                continue
            cls.Configuration.add_or_edit_context(
                section, whoami["Account"], access, secret
            )
            print(
                f"Added {section} context from aws credentials file",
                file=sys.stderr,
            )

    @staticmethod
    def color(name, fallback=None):
        """
        Fetch a scheme color by name, with an optional fallback color if the main requested color is not present.
        """
        if Common.Configuration is None:
            raise ValueError("Configuration is not initialized.")
        if name not in Common.Configuration.scheme["colors"]:
            if fallback is None:
                raise KeyError(f'Undefined color "{name}"')
            return Common.color(fallback)
        return Color(
            Palette8Bit(),
            Common.Configuration.scheme["colors"][name]["foreground"],
            background=Common.Configuration.scheme["colors"][name]["background"],
        )

    @staticmethod
    def border(name, fallback=None):
        """
        Fetch a scheme border style by name, with an optional fallback border style if the main requested style is not present.
        """
        if Common.Configuration is None:
            raise ValueError("Configuration is not initialized.")
        if name not in Common.Configuration.scheme["borders"]:
            if fallback is None:
                raise KeyError(f'Undefined border "{name}"')
            return Common.border(fallback)
        border = Common.Configuration.scheme["borders"][name]
        return BorderStyle(
            [
                border["horizontal"],
                border["vertical"],
                border["TL"],
                border["TR"],
                border["BL"],
                border["BR"],
            ]
        )

    @staticmethod
    def main():
        """
        Main loop method. Passes main loop control to termui.
        """
        Common.Session.ui.main()

    @staticmethod
    def confdir():
        """
        Configuration directory retriever.

        Returns
        -------
        pathlib.Path
            The path of the configuration directory.
        """
        return Path.home() / ".config" / "awsc"

    @staticmethod
    def textlog(message):
        """
        Logs text to stderr, for instances where internal logging doesn't cut it.

        Parameters
        ----------
        message : str
            The message to log.
        """
        print(message, file=sys.stderr)

    @classmethod
    def log(
        cls,
        message,
        summary,
        category,
        message_type,
        subcategory=None,
        resource=None,
        set_message=True,
        **kwargs,
    ):
        """
        Logs a message to the log stash and saves it to disk.

        Parameters
        ----------
        message : str
            The full message to log.
        summary : str
            A short summary of the event being logged.
        category : str
            The category of the logged event.
        message_type : str
            The message type. Severity, but simpler. Expects one of "success", "info" or "error", but more may be defined as long as the scheme
            defines a color for it.
        subcategory : str
            The subcategory of the logged event.
        resource : str
            The resource identifier which triggered the event.
        set_message : bool
            Whether to also flash a message on the awsc message display about this event. The flashed message is the message.
        kwargs : dict
            Any additional keyword arguments will be logged as context for the event.
        """
        cls._logholder.log(
            message,
            summary,
            category,
            message_type,
            subcategory=subcategory,
            resource=resource,
            set_message=set_message,
            **kwargs,
        )

    @classmethod
    def error(
        cls,
        message,
        summary,
        category,
        subcategory=None,
        resource=None,
        set_message=True,
        **kwargs,
    ):
        """
        Shorthand for log(message_type="error").

        See documentation of awsc.log() for parameter descriptions.
        """
        cls.log(
            message,
            summary,
            category,
            "error",
            subcategory=subcategory,
            resource=resource,
            set_message=set_message,
            **kwargs,
        )

    @classmethod
    def log_exception(
        cls,
        exception,
        category,
        subcategory=None,
        resource=None,
        set_message=True,
        **kwargs,
    ):
        """
        Shorthand for error(message=str(exception), summary=type(exception)). Also logs traceback.

        See documentation of awsc.log() for parameter descriptions.

        Parameters
        ----------
        exception : Exception
            Any exception object.
        """
        trace = "".join(traceback.format_tb(exception.__traceback__))
        cls.error(
            f"{str(exception)}\nTraceback:\n{trace}",
            type(exception).__name__,
            category,
            subcategory=subcategory,
            resource=resource,
            set_message=set_message,
            **kwargs,
        )

    @classmethod
    def clienterror(
        cls,
        error,
        summary,
        category,
        subcategory=None,
        resource=None,
        set_message=True,
        **kwargs,
    ):
        """
        Shorthand for extracting the AWS error message and passing it to error().

        See documentation of awsc.log() for parameter descriptions.

        Parameters
        ----------
        error : botocore.exceptions.ClientError
            Any boto3 ClientError derivative.
        """
        errtype = error.response["Error"]["Code"]
        errmsg = error.response["Error"]["Message"]
        cls.log(
            errmsg,
            f"{summary} | AWS: {errtype}",
            category,
            "error",
            subcategory=subcategory,
            resource=resource,
            set_message=set_message,
            **kwargs,
        )

    @classmethod
    def success(
        cls,
        message,
        summary,
        category,
        subcategory=None,
        resource=None,
        set_message=True,
        **kwargs,
    ):
        """
        Shorthand for log(message_type="success")

        See documentation of awsc.log() for parameter descriptions.
        """
        cls.log(
            message,
            summary,
            category,
            "success",
            subcategory=subcategory,
            resource=resource,
            set_message=set_message,
            **kwargs,
        )

    @classmethod
    def info(
        cls,
        message,
        summary,
        category,
        subcategory=None,
        resource=None,
        set_message=True,
        **kwargs,
    ):
        """
        Shorthand for log(message_type="info")

        See documentation of awsc.log() for parameter descriptions.
        """
        cls.log(
            message,
            summary,
            category,
            "info",
            subcategory=subcategory,
            resource=resource,
            set_message=set_message,
            **kwargs,
        )

    @classmethod
    def generic_api_call(
        cls,
        service,
        method,
        api_kwargs,
        summary,
        category,
        subcategory=None,
        success_template=None,
        resource=None,
        **kwargs,
    ):
        """
        Executes an AWS API call. The event is logged and a response is returned.

        See documentation of awsc.log() for parameter descriptions.

        Parameters
        ----------
        service : str
            The boto3 provider for the API call.
        method : str
            The provider's method to call for the API call.
        api_kwargs : dict
            A map of keyword arguments to pass to the method call.
        success_template : str
            A format() string for the message to display when the API call is successful. No message is displayed if omitted.
            Formatting parameters:
            - The "resource" keyword and the 0 index for the value of the resource parameter.
            - All entries in api_kwargs.
            - All entries in kwargs.

        Returns
        -------
        dict
            A dict with two keys.
            - The key "Success" contains a boolean about whether the API call was a success.
            - The "Response" key is a dict. If the call was a success, it is the parsed JSON response from the AWS API. Otherwise, it contains
              the AWS error response. The error response contains the key "Error", which is a dict with the keys "Code" and "Message".
        """
        try:
            response = getattr(cls.Session.service_provider(service), method)(
                **api_kwargs
            )
            if success_template is not None:
                cls.success(
                    success_template.format(
                        resource, resource=resource, **api_kwargs, **kwargs
                    ),
                    summary,
                    category,
                    subcategory=subcategory,
                    resource=resource,
                    set_message=True,
                    api_provider=service,
                    api_method=method,
                    api_args=api_kwargs,
                    **kwargs,
                )
            return {"Success": True, "Response": response}
        except exceptions.ClientError as error:
            cls.clienterror(
                error,
                summary,
                category,
                subcategory=subcategory,
                resource=resource,
                set_message=True,
                api_provider=service,
                api_method=method,
                api_args=api_kwargs,
                **kwargs,
            )
            return {"Success": False, "Response": error.response}
        except Exception as error:
            cls.error(
                str(error),
                summary,
                category,
                subcategory=subcategory,
                resource=resource,
                set_message=True,
                api_provider=service,
                api_method=method,
                api_args=api_kwargs,
                **kwargs,
            )
            return {
                "Success": False,
                "Response": {
                    "Error": {
                        "Code": f"Python.{type(error).__name__}",
                        "Message": str(error),
                    }
                },
            }

    @classmethod
    def textfield_colors(cls, prefix):
        """
        Generates the commonly used color arguments for a textfield dialog given a prefix.

        Parameters
        ----------
        prefix : str
            The prefix for the colors.

        Returns
        -------
        dict
            A partial set of keyword arguments for DialogFieldText().
        """
        return {
            "color": cls.color(
                f"{prefix}_modal_dialog_textfield", "modal_dialog_textfield"
            ),
            "selected_color": cls.color(
                f"{prefix}_modal_dialog_textfield_selected",
                "modal_dialog_textfield_selected",
            ),
            "label_color": cls.color(
                f"{prefix}_modal_dialog_textfield_label", "modal_dialog_textfield_label"
            ),
            "label_min": 16,
        }

    @staticmethod
    def str_attrgetter(attr):
        """
        Returns a sort predicate like attrgetter that forces everything to be a string.

        Parameters
        ----------
        attr : str
            The attribute name for the attrgetter.

        Returns
        -------
        callable(dict) -> object
            Function which returns the named attribute of the parameter.
        """

        def fn(x):
            value = x[attr]
            if value is None:
                return ""
            return str(value)

        return fn


# TODO: Should be a classmethod of Common.
def default_border(prefix, title, title_info=None):
    """
    Generates the default border object for the specified prefix, title and title_info.

    Parameters
    ----------
    prefix : str
        The color scheme prefix for the control which is requesting a border.
    title : str
        The title for the control.
    title_info : str
        The title information for the control.

    Returns
    -------
    awsc.termui.control.Border
        The generated default border.
    """
    return Border(
        Common.border("resource_list", "default"),
        Common.color(f"{prefix}_border", "generic_border"),
        title,
        Common.color(f"{prefix}_border_title", "border_title"),
        title_info,
        Common.color(f"{prefix}_border_title_info", "border_title_info"),
    )


class LogHolder:
    """
    Log stash object. Contains a list of log message from this and past runs. Interacts with the log storage yaml file to store and reload
    log messages.

    Does not need to be instantiated, Common holds an instance of this.

    Attributes
    ----------
    raw_entries : list(dict)
        A list of raw log entries. Raw log entries are in a dict-form, rather than as ListEntry objects.
    control : awsc.log.LogLister
        If the log list control is active, this is a reference to it. Just in case something loggable happens while looking at logs.
    """

    def __init__(self):
        self.raw_entries = []
        self.control = None
        self.parse_log_messages()

    def parse_log_messages(self):
        """
        Reads all raw entries from the disk storage and loads it into raw_entries.
        """
        file = Common.confdir() / "log.yaml"
        if file.exists():
            with file.open("r") as file:
                self.raw_entries = yaml.safe_load(file.read())
        else:
            self.raw_entries = []
        self.parse_raw_entries()

    def parse_raw_entries(self):
        """
        Parses raw entries into the LogLister control if one is active right now.
        """
        if self.control is not None:
            self.control.entries.clear()
            for entry in self.raw_entries:
                self.control.add_raw_entry(entry)
            self.control.sort()

    def write_raw_entries(self):
        """
        Writes the loaded raw entries to disk. Expunges log entries that go over log retention limits on lines or age.
        """
        file_path = Common.confdir() / "log.yaml"
        limit = Common.Configuration["log_retention"]["max_lines"]
        if limit > 0:
            max_idx = limit
        else:
            max_idx = len(self.raw_entries)
        age_limit = Common.Configuration["log_retention"]["max_age"]
        now = datetime.now(timezone.utc).timestamp()
        if age_limit > 0:
            for idx, raw_entry in enumerate(self.raw_entries):
                if now - raw_entry["timestamp"] > age_limit:
                    max_idx = idx
                    break

        self.raw_entries = self.raw_entries[:max_idx]

        with file_path.open("w") as file:
            file.write(yaml.dump(self.raw_entries))

    def attach(self, control):
        """
        Attaches the log stash to a LogLister control and populates it.

        Parameters
        ----------
        control : awsc.termui.LogLister
            The control to attach.
        """
        self.control = control
        for entry in self.raw_entries:
            self.control.add_raw_entry(entry)

    def detach(self):
        """
        Detaches a LogLister control from the log stash, probably because it was closed.
        """
        self.control = None

    def log(
        self,
        message,
        summary,
        category,
        message_type,
        subcategory=None,
        resource=None,
        set_message=True,
        **kwargs,
    ):
        """
        Adds a new log message to the log stash.

        See the documentation of Common.log() for the documentation of the parameters.
        """
        if set_message:
            color = "message_info"
            if message_type == "success":
                color = "message_success"
            elif message_type == "error":
                color = "message_error"
            Common.Session.set_message(message, Common.color(color))
        self.raw_entries.insert(
            0,
            {
                "summary": summary,
                "category": category,
                "subcategory": subcategory,
                "type": message_type,
                "message": message,
                "resource": resource,
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "context": json.dumps(kwargs, default=datetime_hack),
            },
        )
        if self.control is not None:
            self.control.add_raw_entry(self.raw_entries[0])
        self.write_raw_entries()
