import datetime
import os
import sys

from . import resources
from .aws import AWS
from .commander import Commander, Filterer
from .common import BaseChart, Common, DefaultAnchor, DefaultBorder, DefaultDimension
from .context import ContextList
from .info import InfoDisplay
from .log import LogLister, LogViewer
from .meta import CommanderOptionsLister
from .region import RegionList
from .ssh import SSHList
from .termui.alignment import Dimension, TopLeftAnchor
from .termui.control import Border


def awscheck():
    return bool(Common.Session.context) and bool(Common.Session.region)


def open_context_lister():
    ctxl = ContextList(
        Common.Session.ui.top_block,
        DefaultAnchor,
        DefaultDimension,
        border=DefaultBorder("context_list", "Contexts"),
        weight=0,
    )
    return [ctxl, ctxl.hotkey_display]


def open_region_lister():
    regl = RegionList(
        Common.Session.ui.top_block,
        DefaultAnchor,
        DefaultDimension,
        border=DefaultBorder("region_list", "Regions"),
        weight=0,
    )
    return [regl, regl.hotkey_display]


def open_ssh_lister():
    return SSHList.opener()


def open_logs_lister():
    return LogLister.opener()


def open_filterer():
    if Common.Session.filterer is None:
        return Filterer(
            Common.Session.ui.top_block,
            TopLeftAnchor(0, 8),
            Dimension("100%", "3"),
            Common.Session,
            color=Common.color("search_bar_color"),
            symbol_color=Common.color("search_bar_symbol_color"),
            autocomplete_color=Common.color("search_bar_autocomplete_color"),
            inactive_color=Common.color("search_bar_inactive_color"),
            weight=-200,
            border=Border(
                Common.border("search_bar"), Common.color("search_bar_border")
            ),
        )
    else:
        Common.Session.filterer.resume()


def open_commander():
    return Commander(
        Common.Session.ui.top_block,
        TopLeftAnchor(0, 8),
        Dimension("100%", "3"),
        Common.Session,
        color=Common.color("command_bar_color"),
        symbol_color=Common.color("command_bar_symbol_color"),
        autocomplete_color=Common.color("command_bar_autocomplete_color"),
        ok_color=Common.color("command_bar_ok_color"),
        error_color=Common.color("command_bar_error_color"),
        weight=-200,
        border=Border(Common.border("search_bar"), Common.color("search_bar_border")),
    )


def main(*args, **kwargs):
    # stderr hack
    old_stderr = None
    try:
        if os.fstat(0) == os.fstat(1):
            tg = open("error.log", "w", buffering=1)

            old_stderr = sys.stderr
            sys.stderr = tg

        Common.initialize()
        Common.Session.service_provider = AWS()
        Common.post_initialize()
        Common.Session.replace_frame(open_context_lister())

        Common.Session.info_display.commander_hook = open_commander
        Common.Session.info_display.filterer_hook = open_filterer

        Common.Session.commander_options["ctx"] = open_context_lister
        Common.Session.commander_options["context"] = open_context_lister
        Common.Session.commander_options["region"] = open_region_lister
        Common.Session.commander_options["ssh"] = open_ssh_lister
        Common.Session.commander_options["logs"] = open_logs_lister
        Common.Session.commander_options["?"] = CommanderOptionsLister.opener
        Common.Session.commander_options["help"] = CommanderOptionsLister.opener

        Common.main()
    finally:
        if old_stderr is not None:
            sys.stderr.close()
            sys.stderr = old_stderr
