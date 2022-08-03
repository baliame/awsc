import configparser
import json
import sys
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
from .termui.dialog import DialogControl

DefaultAnchor = TopLeftAnchor(0, 11)
DefaultDimension = Dimension("100%", "100%-14")


def datetime_hack(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")


class BaseChart(BarGraph):
    prefix = "CHANGEME"
    title = "CHANGEME"

    @classmethod
    def opener(cls, *args, **kwargs):
        ret = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            *args,
            weight=0,
            color=Common.color("generic"),
            **kwargs,
        )
        ret.border = DefaultBorder(cls.prefix, cls.title, ret.title_info())
        return [ret]

    def title_info(self):
        return None


class SessionAwareDialog(DialogControl):
    @classmethod
    def opener(cls, caller, *args, **kwargs):
        return cls(
            caller.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=caller,
            *args,
            **kwargs,
        )

    def __init__(self, *args, caller, **kwargs):
        caller.dialog_mode = True
        self.caller = caller
        Common.Session.extend_frame(self)
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        super().__init__(*args, **kwargs)

    def input(self, inkey):
        if inkey.is_sequence and inkey.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(inkey)

    def accept_and_close(self):
        self.close()

    def close(self):
        self.caller.dialog_mode = False
        self.parent.remove_block(self)
        Common.Session.remove_from_frame(self)


class Common:
    Configuration = None
    Session = None
    _logholder = None
    initialized = False
    init_hooks: Set[Callable[[], None]] = set()

    @classmethod
    def run_on_init(cls, hook):
        if cls.initialized:
            hook()
        else:
            cls.init_hooks.add(hook)

    @classmethod
    def initialize(cls):
        cls.Configuration = Config()
        cls.Session = Session(
            cls.Configuration,
            cls.color("info_display_title"),
            cls.color("info_display_value"),
            cls,
        )
        cls._logholder = LogHolder()

    @classmethod
    def post_initialize(cls):
        for hook in cls.init_hooks:
            hook()
        cls.load_dot_aws()

    @classmethod
    def load_dot_aws(cls):
        aws_creds = Path.home() / ".aws" / "credentials"
        print("Loading ~/.aws/credentials", file=sys.stderr)
        try:
            with aws_creds.open("r") as f:
                creds = f.read()
        except OSError as e:
            print(
                "Failed to open ~/.aws/credentials: {0}".format(str(e)), file=sys.stderr
            )
            return
        parser = configparser.ConfigParser(default_section="__default")
        parser.read_string(creds)
        for section in parser.sections():
            if "aws_access_key_id" not in parser[section]:
                print(
                    "aws_access_key_id missing for credential {0}, skipping".format(
                        section
                    ),
                    file=sys.stderr,
                )
                continue
            if "aws_secret_access_key" not in parser[section]:
                print(
                    "aws_secret_access_key missing for credential {0}, skipping".format(
                        section
                    ),
                    file=sys.stderr,
                )
                continue
            access = parser[section]["aws_access_key_id"]
            secret = parser[section]["aws_secret_access_key"]
            api_keypair = {"access": access, "secret": secret}
            try:
                whoami = cls.Session.service_provider.whoami(keys=api_keypair)
            except exceptions.ClientError as e:
                cls.clienterror(
                    e,
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
                "Added {0} context from aws credentials file".format(section),
                file=sys.stderr,
            )

    @staticmethod
    def color(name, fallback=None):
        if Common.Configuration is None:
            raise ValueError("Configuration is not initialized.")
        if name not in Common.Configuration.scheme["colors"]:
            if fallback is None:
                raise KeyError('Undefined color "{0}"'.format(name))
            return Common.color(fallback)
        return Color(
            Palette8Bit(),
            Common.Configuration.scheme["colors"][name]["foreground"],
            background=Common.Configuration.scheme["colors"][name]["background"],
        )

    @staticmethod
    def border(name, fallback=None):
        if Common.Configuration is None:
            raise ValueError("Configuration is not initialized.")
        if name not in Common.Configuration.scheme["borders"]:
            if fallback is None:
                raise KeyError('Undefined border "{0}"'.format(name))
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
        Common.Session.ui.main()

    @staticmethod
    def confdir():
        return Path.home() / ".config" / "awsc"

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
        errtype = error.response["Error"]["Code"]
        errmsg = error.response["Error"]["Message"]
        cls.log(
            errmsg,
            "AWS: {0}".format(errtype),
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
        try:
            response = getattr(cls.Session.service_provider(service), method)(
                **api_kwargs
            )
            if success_template is not None:
                cls.success(
                    success_template.format(resource, resource=resource, **api_kwargs),
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
        except exceptions.ClientError as e:
            cls.clienterror(
                e,
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
            return {"Success": False, "Response": e.response}
        except Exception as e:
            cls.error(
                str(e),
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
                        "Code": "Python.{0}".format(type(e).__name__),
                        "Message": str(e),
                    }
                },
            }


def DefaultBorder(prefix, title, title_info=None):
    return Border(
        Common.border("resource_list", "default"),
        Common.color("{0}_border".format(prefix), "generic_border"),
        title,
        Common.color("{0}_border_title".format(prefix), "border_title"),
        title_info,
        Common.color("{0}_border_title_info".format(prefix), "border_title_info"),
    )


class LogHolder:
    def __init__(self):
        self.raw_entries = []
        self.control = None
        self.parse_log_messages()

    def parse_log_messages(self):
        file = Common.confdir() / "log.yaml"
        if file.exists():
            with file.open("r") as f:
                self.raw_entries = yaml.safe_load(f.read())
        else:
            self.raw_entries = []
        self.parse_raw_entries()

    def parse_raw_entries(self):
        if self.control is not None:
            self.control.entries.clear()
            for entry in self.raw_entries:
                self.control.add_raw_entry(entry)
            self.control.sort()

    def write_raw_entries(self):
        file = Common.confdir() / "log.yaml"
        limit = Common.Configuration["log_retention"]["max_lines"]
        if limit > 0:
            max_idx = limit
        else:
            max_idx = len(self.raw_entries)
        age_limit = Common.Configuration["log_retention"]["max_age"]
        now = datetime.now(timezone.utc).timestamp()
        if age_limit > 0:
            for idx in range(len(self.raw_entries)):
                if now - self.raw_entries[idx]["timestamp"] > age_limit:
                    max_idx = idx
                    break

        self.raw_entries = self.raw_entries[:max_idx]

        with file.open("w") as f:
            f.write(yaml.dump(self.raw_entries))

    def attach(self, control):
        self.control = control
        for entry in self.raw_entries:
            self.control.add_raw_entry(entry)

    def detach(self):
        self.control = None

    def add_raw_entry(self, entry):
        if self.control is not None:
            self.control.add_raw_entry(entry)
        self.write_raw_entries()

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
        self.add_raw_entry(self.raw_entries[0])
