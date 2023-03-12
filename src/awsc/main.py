"""
Main module for the awsc application.
"""
import argparse
import configparser
import os
import sys
from pathlib import Path

import boto3

# pylint: disable=unused-import # We use this import to enumerate all resource listers.
from . import resources
from .aws import AWS
from .commander import Commander, Filterer
from .common import Common, DefaultAnchor, DefaultDimension
from .context import ContextList
from .dashboard import Dashboard
from .log import LogLister
from .meta import CommanderOptionsLister
from .region import RegionList
from .ssh import SSHList
from .termui.alignment import Dimension, TopLeftAnchor
from .termui.control import Border


def awscheck():
    """
    Predicate function for checking if AWS is initialized.
    """
    return bool(Common.Session.context) and bool(Common.Session.region)


def open_filterer():
    """
    Hotkey callback for opening the filter bar.
    """
    if Common.Session.filterer is None:
        return Filterer(
            Common.Session.ui.top_block,
            TopLeftAnchor(0, 8),
            Dimension("100%", "3"),
            session=Common.Session,
            color=Common.color("search_bar_color"),
            symbol_color=Common.color("search_bar_symbol_color"),
            inactive_color=Common.color("search_bar_inactive_color"),
            weight=-200,
            border=Border(
                Common.border("search_bar"), Common.color("search_bar_border")
            ),
        )
    return Common.Session.filterer.resume()


def open_commander():
    """
    Hotkey callback for opening the command palette.
    """
    return Commander(
        Common.Session.ui.top_block,
        TopLeftAnchor(0, 8),
        Dimension("100%", "3"),
        session=Common.Session,
        color=Common.color("command_bar_color"),
        symbol_color=Common.color("command_bar_symbol_color"),
        autocomplete_color=Common.color("command_bar_autocomplete_color"),
        ok_color=Common.color("command_bar_ok_color"),
        error_color=Common.color("command_bar_error_color"),
        weight=-200,
        border=Border(Common.border("search_bar"), Common.color("search_bar_border")),
    )


def main(*args, **kwargs):
    """
    Entrypoint for awsc.
    """
    # stderr hack
    old_stderr = None
    try:
        Common.initialize()

        if os.fstat(0) == os.fstat(1):
            # pylint: disable=consider-using-with # With would be extremely roundabout here.
            log_file_handle = open(
                Common.Configuration["error_log"], "w", buffering=1, encoding="utf-8"
            )
            old_stderr = sys.stderr
            sys.stderr = log_file_handle
        Common.Session.service_provider = AWS()
        Common.post_initialize()
        if Common.Session.context == "":
            Common.Session.replace_frame(ContextList.opener())
        else:
            if Common.Session.context_data["mfa_device"] != "":
                Common.Session.replace_frame(ContextList.opener())
            else:
                Common.Session.replace_frame(Dashboard.opener())

        Common.Session.info_display.commander_hook = open_commander
        Common.Session.info_display.filterer_hook = open_filterer

        Common.Session.commander_options["ctx"] = ContextList.opener
        Common.Session.commander_options["context"] = ContextList.opener
        Common.Session.commander_options["region"] = RegionList.opener
        Common.Session.commander_options["ssh"] = SSHList.opener
        Common.Session.commander_options["logs"] = LogLister.opener
        Common.Session.commander_options["?"] = CommanderOptionsLister.opener
        Common.Session.commander_options["help"] = CommanderOptionsLister.opener

        Common.main()
    finally:
        if old_stderr is not None:
            sys.stderr.close()
            sys.stderr = old_stderr


def cred_helper(*args, **kwargs):
    parser = argparse.ArgumentParser(
        prog="AWSC Credentials Helper",
        description="Allows access to awsc credentials keystore for use with aws cli",
    )
    parser.add_argument("context")
    args = parser.parse_args()
    Common.initialize()
    conf = Common.Configuration
    if args.context not in conf.keystore:
        print(f"Keypair {args.context} not found.", file=sys.stderr)
    keypair = conf.keystore[args.context]
    sts = boto3.client(
        "sts",
        aws_access_key_id=keypair["access"],
        aws_secret_access_key=keypair["secret"],
    )
    context = conf["contexts"][args.context]
    if context["mfa_device"] != "":
        mfa_code = input(f"Enter MFA code for device {context['mfa_device']}: ")
        resp = sts.get_session_token(
            DurationSeconds=86400,
            SerialNumber=context["mfa_device"],
            TokenCode=mfa_code,
        )
    else:
        resp = sts.get_session_token(DurationSeconds=86400)

    aws_creds = Path.home() / ".aws" / "credentials"
    try:
        with aws_creds.open("r", encoding="utf-8") as file:
            creds = file.read()
    except OSError as error:
        if error.errno == 2:  # FNF
            creds = ""
        else:
            print(
                f"Failed to open ~/.aws/credentials: {str(error)}",
                file=sys.stderr,
            )
            return

    parser = configparser.ConfigParser(default_section="__default")
    parser.read_string(creds)
    if parser.has_section(args.context):
        parser.remove_section(args.context)
    parser.add_section(args.context)

    token = resp["Credentials"]["SessionToken"]
    expiration = resp["Credentials"]["Expiration"]
    parser.set(args.context, "aws_session_token", token)
    parser.set(args.context, "aws_security_token", token)
    parser.set(
        args.context,
        "expiration",
        expiration.strftime("%Y-%m-%d %H:%M:%S"),
    )
    parser.set(
        args.context,
        "aws_access_key_id",
        resp["Credentials"]["AccessKeyId"],
    )
    parser.set(
        args.context,
        "aws_secret_access_key",
        resp["Credentials"]["SecretAccessKey"],
    )

    with aws_creds.open("w", encoding="utf-8") as file:
        parser.write(file)
    print(f"Wrote short term token to profile {args.context}", file=sys.stderr)
