"""
Main module for the awsc application.
"""
import os
import sys

# pylint: disable=unused-import # We use this import to enumerate all resource listers.
from . import resources
from .aws import AWS
from .commander import Commander, Filterer
from .common import Common, DefaultAnchor, DefaultDimension, default_border
from .context import ContextList
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
        if os.fstat(0) == os.fstat(1):
            # pylint: disable=consider-using-with # With would be extremely roundabout here.
            log_file_handle = open("error.log", "w", buffering=1, encoding="utf-8")

            old_stderr = sys.stderr
            sys.stderr = log_file_handle

        Common.initialize()
        Common.Session.service_provider = AWS()
        Common.post_initialize()
        Common.Session.replace_frame(ContextList.opener())

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
