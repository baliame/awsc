import datetime
import json
import threading
import traceback
from typing import List

import pyperclip
from botocore import exceptions as botoerror

from .common import (
    Common,
    DefaultAnchor,
    DefaultBorder,
    DefaultDimension,
    SessionAwareDialog,
)
from .info import HotkeyDisplay
from .termui.alignment import CenterAnchor, Dimension, TopRightAnchor
from .termui.color import ColorBlackOnGold, ColorBlackOnOrange, ColorGold
from .termui.control import Border
from .termui.dialog import (
    DialogField,
    DialogFieldCheckbox,
    DialogFieldLabel,
    DialogFieldText,
)
from .termui.list_control import ListControl, ListEntry
from .termui.text_browser import TextBrowser
from .termui.ui import ControlCodes


def datetime_hack(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")


class StopLoadingData(Exception):
    pass


class ResourceListerBase(ListControl):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, "primary_key"):
            self.primary_key = None
        self.load_counter = 1
        self.dialog_mode = False
        self.closed = False
        if not hasattr(self, "next_marker"):
            self.next_marker = None
        if not hasattr(self, "next_marker_arg"):
            self.next_marker_arg = None
        self.auto_refresh_last = datetime.datetime.now()
        super().__init__(*args, **kwargs)

    def on_close(self):
        self.closed = True

    def auto_refresh(self):
        pass

    def asynch(self, fn, *args, clear=False, **kwargs):
        try:
            t = threading.Thread(
                target=self.async_inner,
                args=args,
                kwargs={**kwargs, "fn": fn, "clear": clear},
                daemon=True,
            )
            t.start()
        except Exception as e:  # pylint: disable=broad-except # Purpose of this function is extremely generic
            Common.Session.set_message(
                "Failed to start AWS query thread: {0}".format(str(e)),
                Common.color("message_error"),
            )

    def before_paint_critical(self):
        super().before_paint_critical()
        if "thread_error" in self.thread_share:
            Common.Session.set_message(
                self.thread_share["thread_error"], Common.color("message_error")
            )
            del self.thread_share["thread_error"]

    def async_inner(self, *args, fn, clear=False, **kwargs):
        try:
            self.mutex.acquire()
            try:
                if clear or (
                    not hasattr(self, "primary_key") or self.primary_key is None
                ):
                    self.thread_share["clear"] = True
            finally:
                self.mutex.release()

            for data in fn(*args, **kwargs):
                self.mutex.acquire()
                try:
                    self.thread_share["new_entries"].extend(data)
                finally:
                    self.mutex.release()

        except StopLoadingData:
            pass
        except Exception as e:  # pylint: disable=broad-except # Purpose of this function is extremely generic, needs a catch-all
            self.thread_share[
                "thread_error"
            ] = "Refresh thread execution failed: {0}: {1}".format(
                e.__class__.__name__, str(e)
            )
            Common.error(
                "Refresh thread execution failed: {0}: {1}\n{2}".format(
                    e.__class__.__name__, str(e), traceback.format_exc()
                ),
                "Refresh Thread Error",
                "Core",
                set_message=False,
            )
            Common.Session.set_message(
                "Refresh thread execution failed", Common.color("message_error")
            )
        self.mutex.acquire()
        try:
            self.thread_share["updating"] = False
            self.thread_share["finalize"] = True
        finally:
            self.mutex.release()

    def handle_finalization_critical(self):
        if hasattr(self, "primary_key") and self.primary_key is not None:
            ne = []
            for entry in self.entries:
                if entry[self.primary_key] in self.thread_share["acquired"]:
                    ne.append(entry)
            self.entries = ne[:]
            self.sort()

    def handle_new_entries_critical(self, entries):
        if not hasattr(self, "primary_key") or self.primary_key is None:
            super().handle_new_entries_critical(entries)
        else:
            for new in entries:
                found = False
                for old in self.entries:
                    if old[self.primary_key] == new[self.primary_key]:
                        old.mutate(new)
                        found = True
                        break
                if not found:
                    self.entries.append(new)
                self.thread_share["acquired"].append(new[self.primary_key])

    def get_data_generic(
        self,
        resource_key,
        list_method,
        list_kwargs,
        item_path,
        column_paths,
        hidden_columns,
        next_marker_name,
        next_marker_arg,
        *args
    ):
        try:
            provider = Common.Session.service_provider(resource_key)
        except KeyError:
            return
        if callable(list_kwargs):
            list_kwargs = list_kwargs()
        ret = []
        next_marker = None
        while next_marker != "":
            if self.closed:
                raise StopLoadingData
            it_list_kwargs = list_kwargs.copy()
            if next_marker is not None and next_marker_arg is not None:
                it_list_kwargs[next_marker_arg] = next_marker
            response = getattr(provider, list_method)(**it_list_kwargs)

            it = (
                Common.Session.jq(item_path)
                .input(text=json.dumps(response, default=datetime_hack))
                .first()
            )
            if it is None:
                Common.error(
                    "get_data_generic returned None for {0}.{1}({2}) on path {3}\nAPI response was:\n{4}".format(
                        resource_key,
                        list_method,
                        list_kwargs,
                        item_path,
                        json.dumps(response, default=datetime_hack),
                    ),
                    "Get Data Generic returned None",
                    "Core",
                    set_message=False,
                )
                return []

            for item in it:
                if self.closed:
                    raise StopLoadingData
                init = {}
                for column, path in {**column_paths, **hidden_columns}.items():
                    if callable(path):
                        init[column] = path(item)
                    else:
                        try:
                            init[column] = Common.Session.jq(path).input(item).first()
                        except StopIteration:
                            init[column] = ""
                le = ListEntry(**init)
                le.controller_data = item
                if self.matches(le, *args):
                    ret.append(le)
            if self.closed:
                raise StopLoadingData
            yield ret
            if self.closed:
                raise StopLoadingData
            self.load_counter += 1
            if next_marker_name is not None and next_marker_name in response:
                next_marker = response[next_marker_name]
                ret = []
            else:
                next_marker = ""

    def matches(self, list_entry, *args):
        return True

    def tag_finder_generator(self, tagname, default="", taglist_key="Tags"):
        def fn(e, *args):
            if taglist_key in e:
                for tag in e[taglist_key]:
                    if tag["Key"] == tagname:
                        return tag["Value"]
            return default

        return fn

    def empty(self, _):
        return ""


class DialogFieldButton(DialogField):
    def __init__(self, text, action, color=ColorGold, selected_color=ColorBlackOnGold):
        super().__init__()
        self.highlightable = True
        self.text = text
        self.color = color
        self.selected_color = selected_color
        self.centered = True
        self.action = action

    def input(self, inkey):
        if inkey.is_sequence and inkey.name == "KEY_ENTER":
            self.action()
            Commons.UIInstance.dirty = True
        return True

    def paint(self, x0, x1, y, selected=False):
        x = x0
        if self.centered:
            textlen = len(self.text) + 4
            w = x1 - x0 + 1
            x = int(w / 2) - int(textlen / 2) + x0


class DialogFieldResourceListSelector(DialogField):
    def __init__(
        self,
        selector_class,
        label,
        default="",
        color=ColorBlackOnOrange,
        selected_color=ColorBlackOnGold,
        label_color=ColorGold,
        label_min=0,
        primary_key=None,
    ):
        super().__init__()
        self.highlightable = True
        self.left = 0
        self.text = default
        self.label = label
        self.color = color
        self.label_color = label_color
        self.label_min = label_min
        self.selected_color = selected_color
        self.centered = True
        self.selector_class = selector_class
        self.primary_key = primary_key

    def selector_callback(self, entry):
        self.text = entry

    def input(self, inkey):
        if inkey.is_sequence:
            if inkey.name == "KEY_ENTER":
                kwa = {}
                if self.primary_key is not None:
                    kwa["primary_key"] = self.primary_key
                Common.Session.push_frame(
                    self.selector_class.selector(self.selector_callback, **kwa)
                )
                Common.Session.ui.dirty = True
                return True
            elif inkey.name == "KEY_BACKSPACE" or inkey.name == "KEY_DELETE":
                self.text = ""
                Common.Session.ui.dirty = True
                return True
        return False

    def paint(self, x0, x1, y, selected=False):
        x = x0
        Common.Session.ui.print(self.label, xy=(x, y), color=self.label_color)
        x += max(len(self.label) + 1, self.label_min)
        space = x1 - x + 1
        t = self.text + " ↲"
        if self.left >= len(t):
            self.left = 0
        text = t[
            self.left : (self.left + space if len(t) > self.left + space else len(t))
        ]
        Common.Session.ui.print(
            text, xy=(x, y), color=self.selected_color if selected else self.color
        )


class SingleNameDialog(SessionAwareDialog):
    def __init__(
        self,
        parent,
        title,
        callback,
        *args,
        label="Name:",
        what="name",
        subject="",
        default="",
        caller=None,
        accepted_inputs=None,
        **kwargs
    ):
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            title,
            Common.color("modal_dialog_border_title"),
        )
        super().__init__(
            parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=caller,
            *args,
            **kwargs,
        )
        self.what = what
        self.add_field(
            DialogFieldLabel(
                "Enter {0}{1}".format(
                    what, " for {0}".format(subject) if subject != "" else ""
                )
            )
        )
        self.error_label = DialogFieldLabel(
            "", default_color=Common.color("modal_dialog_error")
        )
        self.add_field(self.error_label)
        self.add_field(DialogFieldLabel(""))
        self.name_field = DialogFieldText(
            label,
            label_min=16,
            color=Common.color("modal_dialog_textfield"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
            label_color=Common.color("modal_dialog_textfield_label"),
            accepted_inputs=accepted_inputs,
        )
        self.add_field(self.name_field)
        self.caller = caller
        self.callback = callback

    def accept_and_close(self):
        if self.name_field.text == "":
            self.error_label.text = "You must enter a {0}.".format(self.what)
            return
        self.callback(self.name_field.text)
        super().accept_and_close()

    def close(self):
        if self.caller is not None:
            self.caller.refresh_data()
        super().close()


class SingleSelectorDialog(SessionAwareDialog):
    def __init__(
        self,
        parent,
        title,
        resource_type,
        action_name,
        selector_class,
        callback,
        *args,
        caller=None,
        **kwargs
    ):
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            title,
            Common.color("modal_dialog_border_title"),
        )
        super().__init__(
            parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            *args,
            caller=caller,
            **kwargs,
        )
        self.add_field(
            DialogFieldLabel(
                "Select {0} for {1} action".format(resource_type, action_name)
            )
        )
        self.error_label = DialogFieldLabel(
            "", default_color=Common.color("modal_dialog_error")
        )
        self.add_field(self.error_label)
        self.add_field(DialogFieldLabel(""))
        self.resource_selector = DialogFieldResourceListSelector(
            selector_class,
            "{0}: ".format(resource_type),
            "",
            label_min=16,
            color=Common.color("modal_dialog_textfield"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
            label_color=Common.color("modal_dialog_textfield_label"),
        )
        self.add_field(self.resource_selector)
        self.caller = caller
        self.callback = callback

    def accept_and_close(self):
        if self.resource_selector.text == "":
            self.error_label.text = "You must select a resource."
            return
        self.callback(self.resource_selector.text)
        super().accept_and_close()

    def close(self):
        if self.caller is not None:
            self.caller.refresh_data()
        super().close()


class ResourceLister(ResourceListerBase):
    prefix = "CHANGEME"
    title = "CHANGEME"
    command_palette: List[str] = []

    @classmethod
    def register(cls):
        for cmd in cls.command_palette:
            Common.Session.commander_options[cmd] = cls.opener
        for subcls in cls.__subclasses__():
            subcls.register()

    @classmethod
    def opener(cls, **kwargs):
        l = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            color=Common.color("{0}_generic".format(cls.prefix), "generic"),
            selection_color=Common.color(
                "{0}_selection".format(cls.prefix), "selection"
            ),
            title_color=Common.color("{0}_heading".format(cls.prefix), "column_title"),
            update_color=Common.color("{0}_updated".format(cls.prefix), "highlight"),
            update_selection_color=Common.color(
                "{0}_updated".format(cls.prefix), "highlight_selection"
            ),
            **kwargs,
        )
        l.border = DefaultBorder(cls.prefix, cls.title, l.title_info())
        return [l, l.hotkey_display]

    @classmethod
    def selector(cls, cb, **kwargs):
        return cls.opener(**{"selector_cb": cb, **kwargs})

    def title_info(self):
        return None

    def __init__(
        self, parent, alignment, dimensions, *args, selector_cb=None, **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        if not hasattr(self, "resource_key"):
            raise AttributeError("resource_key is undefined")
        if not hasattr(self, "list_method"):
            raise AttributeError("list_method is undefined")
        if not hasattr(self, "list_kwargs"):
            if "list_kwargs" in kwargs:
                self.list_kwargs = kwargs["list_kwargs"]
            else:
                self.list_kwargs = {}
        if not hasattr(self, "describe_kwargs"):
            self.describe_kwargs = {}
        if not hasattr(self, "describe_command"):
            self.describe_command = None
        else:
            if not hasattr(self, "describe_selection_arg"):
                self.describe_selection_arg = "entry"
        if not hasattr(self, "open_command") or self.open_command is None:
            self.open_command = None
        else:
            if not isinstance(self.open_command, str):
                if not hasattr(self, "open_selection_arg"):
                    raise AttributeError(
                        "open_command is defined but open_selection_arg is undefined"
                    )
            elif (
                not hasattr(self, "additional_commands")
                or self.open_command not in self.additional_commands
            ):
                raise AttributeError(
                    "open_command refers to a key that is not in additional_commands"
                )
        if not hasattr(self, "item_path"):
            raise AttributeError("item_path is undefined")
        if not hasattr(self, "hidden_columns"):
            self.hidden_columns = {}
        if not hasattr(self, "column_paths"):
            raise AttributeError("column_paths is undefined")

        if "name" not in self.column_paths and "name" not in self.hidden_columns:
            raise AttributeError(
                "name entry is required in column_paths or hidden_columns"
            )
        if not hasattr(self, "imported_column_sizes"):
            self.imported_column_sizes = {
                k: len(k) for k in self.column_paths.keys() if k != "name"
            }
        if not hasattr(self, "imported_column_order"):
            self.imported_column_order = sorted(
                [k for k in self.column_paths.keys() if k != "name"]
            )
        if not hasattr(self, "sort_column"):
            self.sort_column = "name"
        if not hasattr(self, "primary_key") or self.primary_key is None:
            self.primary_key = "name"
        if "primary_key" in kwargs:
            self.primary_key = kwargs["primary_key"]
        if "update_color" in kwargs:
            self.update_color = kwargs["update_color"]
        else:
            self.update_color = self.color
        if "update_selection_color" in kwargs:
            self.update_selection_color = kwargs["update_selection_color"]
        else:
            self.update_selection_color = self.selection_color

        self.selector_cb = selector_cb

        if self.open_command is not None:
            open_tooltip = "Open"
            if isinstance(self.open_command, str):
                cmd = self.additional_commands[self.open_command]
                self.open_command = cmd["command"]
                self.open_selection_arg = cmd["selection_arg"]
                open_tooltip = cmd["tooltip"]
            if selector_cb is None:
                self.add_hotkey("KEY_ENTER", self.open, open_tooltip)
            else:
                self.add_hotkey("o", self.open, open_tooltip)
        if self.describe_command is not None:
            describe_tooltip = "Describe"
            if isinstance(self.describe_command, str):
                cmd = self.additional_commands[self.describe_command]
                self.describe_command = cmd["command"]
                self.describe_selection_arg = cmd["selection_arg"]
                describe_tooltip = cmd["tooltip"]
            self.add_hotkey("d", self.describe, "Describe")
            if self.open_command is None and selector_cb is None:
                self.add_hotkey("KEY_ENTER", self.describe, describe_tooltip)
        if selector_cb is not None:
            self.add_hotkey("KEY_ENTER", self.select_and_close, "Select")
        if hasattr(self, "additional_commands"):
            for key, command_spec in self.additional_commands.items():
                if "kwargs" not in command_spec:
                    command_spec["kwargs"] = {}
                self.add_hotkey(
                    key,
                    self.command_wrapper(
                        command_spec["command"],
                        command_spec["selection_arg"],
                        **command_spec["kwargs"],
                    ),
                    command_spec["tooltip"],
                )
        self.add_hotkey(ControlCodes.R, self.refresh_data, "Refresh")
        if "arn" in self.column_paths or "arn" in self.hidden_columns:
            self.add_hotkey("r", self.copy_arn, "Copy ARN")
        self.hotkey_display = HotkeyDisplay(
            self.parent,
            TopRightAnchor(1, 0),
            Dimension("33%|50", 8),
            self,
            session=Common.Session,
            highlight_color=Common.color("hotkey_display_title"),
            generic_color=Common.color("hotkey_display_value"),
        )

        if "name" in self.imported_column_sizes or "name" in self.hidden_columns:
            self.column_titles = {}
        self.column_titles.update(self.imported_column_sizes)
        if "name" in self.imported_column_order or "name" in self.hidden_columns:
            self.column_order = []
        self.column_order.extend(self.imported_column_order)
        self.refresh_data()

    def copy_arn(self, *args):
        if self.selection is not None:
            pyperclip.copy(self.selection["arn"])
            Common.Session.set_message(
                "Copied resource ARN to clipboard", Common.color("message_success")
            )

    def select_and_close(self, *args):
        import sys

        print("self.selection is {0}".format(self.selection), file=sys.stderr)
        print("self.selector_cb is {0}".format(self.selector_cb), file=sys.stderr)
        print("self.primary_key is {0}".format(self.primary_key), file=sys.stderr)
        if (
            self.selection is not None
            and self.selector_cb is not None
            and self.primary_key is not None
        ):
            self.selector_cb(self.selection[self.primary_key])
            Common.Session.pop_frame()

    def command(self, cmd, kw={}):
        if self.selection is not None:
            frame = cmd(**kw)
            if frame is not None:
                Common.Session.push_frame(frame)

    def command_wrapper(self, cmd, selection_arg, **kwargs):
        def fn(*args):
            self.command(
                cmd,
                {
                    selection_arg: self.selection,
                    "pushed": True,
                    "caller": self,
                    **kwargs,
                },
            )

        return fn

    def describe(self, *args):
        if self.describe_command is not None:
            self.command_wrapper(
                self.describe_command,
                self.describe_selection_arg,
                **self.describe_kwargs,
            )()

    def open(self, *args):
        if self.open_command is not None:
            self.command_wrapper(self.open_command, self.open_selection_arg)()

    def get_data(self, *args, **kwargs):
        for y in self.get_data_generic(
            self.resource_key,
            self.list_method,
            self.list_kwargs,
            self.item_path,
            self.column_paths,
            self.hidden_columns,
            self.next_marker,
            self.next_marker_arg,
        ):
            yield y

    def auto_refresh(self):
        if self.dialog_mode or self.primary_key is None:
            return
        if datetime.datetime.now() - self.auto_refresh_last > datetime.timedelta(
            seconds=10
        ):
            self.refresh_data()

    def refresh_data(self, *args, **kwargs):
        self.mutex.acquire()
        try:
            if "updating" in self.thread_share and self.thread_share["updating"]:
                return
            self.thread_share["updating"] = True
            self.thread_share["acquired"] = []
        finally:
            self.mutex.release()
        self.auto_refresh_last = datetime.datetime.now()
        self.asynch(self.get_data)

    def sort(self):
        self.entries.sort(key=lambda x: x.columns[self.sort_column])
        self._cache = None


class NoResults(Exception):
    pass


class SingleRelationLister(ResourceListerBase):
    prefix = "CHANGEME"
    title = "CHANGEME"

    @classmethod
    def opener(cls, **kwargs):
        l = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            color=Common.color("{0}_generic".format(cls.prefix), "generic"),
            selection_color=Common.color(
                "{0}_selection".format(cls.prefix), "selection"
            ),
            title_color=Common.color("{0}_heading".format(cls.prefix), "column_title"),
            **kwargs,
        )
        l.border = DefaultBorder(cls.prefix, cls.title, l.title_info())
        return [l, l.hotkey_display]

    def __init__(self, parent, alignment, dimensions, *args, **kwargs):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        self.column_order = []
        self.column_titles = {}
        self.add_column("type", 30, 0)
        self.add_column("id", 120, 1)
        if not hasattr(self, "resource_key"):
            raise AttributeError("resource_key is undefined")
        if not hasattr(self, "describe_method"):
            raise AttributeError("describe_method is undefined")
        if not hasattr(self, "describe_kwargs"):
            raise AttributeError("describe_kwargs is undefined")
        if not hasattr(self, "object_path"):
            raise AttributeError("object_path is undefined")
        if not hasattr(self, "sort_column"):
            self.sort_column = "type"
        if not hasattr(self, "resource_descriptors"):
            raise AttributeError("resource_descriptors is undefined")
        self.descriptor = None
        self.descriptor_raw = None
        self.add_hotkey("d", self.describe, "Describe")
        self.add_hotkey("KEY_ENTER", self.describe, "Describe")
        self.hotkey_display = HotkeyDisplay(
            self.parent,
            TopRightAnchor(1, 0),
            Dimension("33%|50", 8),
            self,
            session=Common.Session,
            highlight_color=Common.color("hotkey_display_title"),
            generic_color=Common.color("hotkey_display_value"),
        )
        self.refresh_data()

    def describe(self, _):
        if self.selection is not None:
            if "describer" not in self.selection.controller_data:
                Common.Session.set_message(
                    "Resource cannot be described", Common.color("message_info")
                )
                return
            Common.Session.push_frame(
                self.selection.controller_data["describer"](
                    entry=self.selection, entry_key="id"
                )
            )

    def get_data(self, *args, **kwargs):
        if self.descriptor is None:
            try:
                provider = Common.Session.service_provider(self.resource_key)
            except KeyError:
                return
            resp = getattr(provider, self.describe_method)(**self.describe_kwargs)
            self.descriptor = (
                Common.Session.jq(self.object_path)
                .input(text=json.dumps(resp, default=datetime_hack))
                .first()
            )
            self.descriptor_raw = json.dumps(self.descriptor, default=datetime_hack)
        for elem in self.resource_descriptors:
            try:
                result = (
                    Common.Session.jq(elem["base_path"])
                    .input(text=self.descriptor_raw)
                    .first()
                )
                yield [
                    ListEntry(item, id=item, type=elem["type"], controller_data=elem)
                    for item in result
                ]
            except StopIteration:
                continue
            except ValueError:
                continue

    def refresh_data(self, *args, **kwargs):
        self.asynch(self.get_data, clear=True)

    def sort(self):
        self.entries.sort(key=lambda x: x.columns[self.sort_column])
        self._cache = None


class MultiLister(ResourceListerBase):
    prefix = "CHANGEME"
    title = "CHANGEME"

    @classmethod
    def opener(cls, **kwargs):
        l = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            color=Common.color("{0}_generic".format(cls.prefix), "generic"),
            selection_color=Common.color(
                "{0}_selection".format(cls.prefix), "selection"
            ),
            title_color=Common.color("{0}_heading".format(cls.prefix), "column_title"),
            **kwargs,
        )
        l.border = DefaultBorder(cls.prefix, cls.title, l.title_info())
        return [l, l.hotkey_display]

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        compare_value,
        *args,
        compare_key="id",
        **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        self.add_column("type", 30, 0)
        self.add_column("id", 30, 1)
        if not hasattr(self, "resource_descriptors"):
            raise AttributeError("resource_descriptors is undefined")
        if isinstance(compare_value, ListEntry):
            self.compare_value = compare_value[compare_key]
            self.orig_compare_value = compare_value
        else:
            self.compare_value = compare_value
            self.orig_compare_value = compare_value
        self.add_hotkey("KEY_ENTER", self.describe, "Describe")
        self.add_hotkey("d", self.describe, "Describe")
        self.add_hotkey(ControlCodes.R, self.refresh_data, "Refresh")
        self.hotkey_display = HotkeyDisplay(
            self.parent,
            TopRightAnchor(1, 0),
            Dimension("33%|50", 8),
            self,
            session=Common.Session,
            highlight_color=Common.color("hotkey_display_title"),
            generic_color=Common.color("hotkey_display_value"),
        )
        self.refresh_data()

    def describe(self, *args):
        if self.selection is not None:
            Common.Session.push_frame(
                GenericDescriber.opener(
                    **{
                        "describing": self.selection["id"],
                        "content": json.dumps(
                            self.selection.controller_data, sort_keys=True, indent=2
                        ),
                        "pushed": True,
                    }
                )
            )

    def get_data(self, *args, **kwargs):
        for elem in self.resource_descriptors:
            try:
                for y in self.get_data_generic(
                    elem["resource_key"],
                    elem["list_method"],
                    elem["list_kwargs"],
                    elem["item_path"],
                    elem["column_paths"],
                    elem["hidden_columns"],
                    None,
                    None,
                    elem,
                ):
                    yield y
            except NoResults:
                continue

    def matches(self, list_entry, elem, *args):
        raw_item = list_entry.controller_data
        if "compare_as_list" not in elem or not elem["compare_as_list"]:
            if callable(elem["compare_path"]):
                val = elem["compare_path"](raw_item)
            else:
                try:
                    val = (
                        Common.Session.jq(elem["compare_path"]).input(raw_item).first()
                    )
                except ValueError as e:
                    return False
                except StopIteration as e:
                    return False
            return val == self.compare_value
        else:
            if callable(elem["compare_path"]):
                return self.compare_value in elem["compare_path"](raw_item)
            else:
                try:
                    for val in (
                        Common.Session.jq(elem["compare_path"]).input(raw_item).first()
                    ):
                        if val == self.compare_value:
                            return True
                except StopIteration as e:
                    return False
        return False

    def refresh_data(self, *args, **kwargs):
        self.asynch(self.get_data, clear=True)

    def sort(self):
        self.entries.sort(key=lambda x: x.columns["type"])
        self._cache = None


class GenericDescriber(TextBrowser):
    prefix = "generic_describer"
    title = "Describe resource"

    @classmethod
    def opener(cls, **kwargs):
        l = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            color=Common.color("{0}_generic".format(cls.prefix), "generic"),
            filtered_color=Common.color("{0}_filtered".format(cls.prefix), "selection"),
            **kwargs,
        )
        l.border = DefaultBorder(cls.prefix, cls.title, l.title_info())
        return [l, l.hotkey_display]

    def title_info(self):
        return self.describing

    def __init__(
        self, parent, alignment, dimensions, describing, content, *args, **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        self.describing = describing
        self.add_text(content)
        self.hotkey_display = HotkeyDisplay(
            self.parent,
            TopRightAnchor(1, 0),
            Dimension("33%|50", 8),
            self,
            session=Common.Session,
            highlight_color=Common.color("hotkey_display_title"),
            generic_color=Common.color("hotkey_display_value"),
        )

    def toggle_wrap(self, *args, **kwargs):
        super().toggle_wrap(*args, **kwargs)
        Common.Session.set_message(
            "Text wrap {0}".format("ON" if self.wrap else "OFF"),
            Common.color("message_info"),
        )


class Describer(TextBrowser):
    prefix = "CHANGEME"
    title = "CHANGEME"

    @classmethod
    def opener(cls, **kwargs):
        l = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            color=Common.color("{0}_generic".format(cls.prefix), "generic"),
            filtered_color=Common.color("{0}_filtered".format(cls.prefix), "selection"),
            syntax_highlighting=True,
            scheme=Common.Configuration.scheme,
            **kwargs,
        )
        l.border = DefaultBorder(cls.prefix, cls.title, l.title_info())
        return [l, l.hotkey_display]

    def title_info(self):
        return self.entry_id

    def populate_entry(self, *args, entry, entry_key, **kwargs):
        if entry is None:
            self.entry = None
            self.entry_id = None
            return
        self.entry = entry
        self.entry_id = entry[entry_key]

    def populate_describe_kwargs(self):
        self.describe_kwargs[self.describe_kwarg_name] = (
            [self.entry_id] if self.describe_kwarg_is_list else self.entry_id
        )

    def __init__(
        self, parent, alignment, dimensions, *args, entry, entry_key, **kwargs
    ):
        self.populate_entry(entry=entry, entry_key=entry_key)
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        if not hasattr(self, "resource_key"):
            raise AttributeError("resource_key is undefined")
        if not hasattr(self, "describe_method"):
            raise AttributeError("describe_method is undefined")
        if not hasattr(self, "describe_kwarg_name") and not hasattr(
            self, "describe_kwargs"
        ):
            raise AttributeError(
                "describe_kwarg_name is undefined and describe_kwargs not set manually"
            )
        if not hasattr(self, "describe_kwarg_is_list"):
            self.describe_kwarg_is_list = False
        if not hasattr(self, "describe_kwargs"):
            self.describe_kwargs = {}
        if not hasattr(self, "object_path"):
            raise AttributeError("object_path is undefined")
        if hasattr(self, "describe_kwarg_name"):
            self.populate_describe_kwargs()

        self.add_hotkey(ControlCodes.R, self.refresh_data, "Refresh")
        self.hotkey_display = HotkeyDisplay(
            self.parent,
            TopRightAnchor(1, 0),
            Dimension("33%|50", 8),
            self,
            session=Common.Session,
            highlight_color=Common.color("hotkey_display_title"),
            generic_color=Common.color("hotkey_display_value"),
        )

        if hasattr(self, "additional_commands"):
            for key, command_spec in self.additional_commands.items():
                if "kwargs" not in command_spec:
                    command_spec[kwargs] = {}
                self.add_hotkey(
                    key,
                    self.command_wrapper(
                        command_spec["command"],
                        command_spec["data_arg"],
                        **command_spec["kwargs"],
                    ),
                    command_spec["tooltip"],
                )

        self.refresh_data()

    def command(self, cmd, kw={}):
        frame = cmd(**kw)
        if frame is not None:
            Common.Session.push_frame(frame)

    def command_wrapper(self, cmd, data_arg, **kwargs):
        def fn(*args):
            self.command(
                cmd,
                {
                    data_arg: "\n".join(self.lines),
                    "pushed": True,
                    "caller": self,
                    **kwargs,
                },
            )

        return fn

    def toggle_wrap(self, *args, **kwargs):
        super().toggle_wrap(*args, **kwargs)
        Common.Session.set_message(
            "Text wrap {0}".format("ON" if self.wrap else "OFF"),
            Common.color("message_info"),
        )

    def refresh_data(self, *args, **kwargs):
        pass

        try:
            provider = Common.Session.service_provider(self.resource_key)
        except KeyError:
            return
        response = getattr(provider, self.describe_method)(**self.describe_kwargs)
        self.clear()
        self.add_text(
            json.dumps(
                Common.Session.jq(self.object_path)
                .input(text=json.dumps(response, default=datetime_hack))
                .first(),
                sort_keys=True,
                indent=2,
            )
        )


class DeleteResourceDialog(SessionAwareDialog):
    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        resource_type,
        resource_identifier,
        callback,
        action_name="Delete",
        from_what=None,
        from_what_name=None,
        undoable=False,
        can_force=False,
        extra_fields={},
        **kwargs
    ):
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            "{1} {0}".format(resource_type, action_name),
            Common.color("modal_dialog_border_title"),
        )
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        label = [
            ("{0} ".format(action_name), Common.color("modal_dialog_label")),
            (resource_type, Common.color("modal_dialog_label_highlight")),
            (' resource "', Common.color("modal_dialog_label")),
            (resource_identifier, Common.color("modal_dialog_label_highlight")),
            ('"', Common.color("modal_dialog_label")),
        ]

        if from_what is not None:
            label.append(
                (" from {0}".format(from_what), Common.color("modal_dialog_label"))
            )
            if from_what_name is not None:
                label.append((' "', Common.color("modal_dialog_label")))
                label.append(
                    (from_what_name, Common.color("modal_dialog_label_highlight"))
                )
                label.append(('"', Common.color("modal_dialog_label")))

        label.append(("?", Common.color("modal_dialog_label")))
        self.add_field(DialogFieldLabel(label))
        if not undoable:
            self.add_field(
                DialogFieldLabel(
                    "This action cannot be undone.", Common.color("modal_dialog_error")
                )
            )
        self.highlighted = 1
        self.can_force = can_force
        if self.can_force:
            self.highlighted += 1
            self.force_checkbox = DialogFieldCheckbox(
                "Force",
                checked=False,
                color=Common.color("modal_dialog_textfield_label"),
                selected_color=Common.color("modal_dialog_textfield_selected"),
            )
            self.add_field(self.force_checkbox)
        self.extra_fields = {}
        for field in extra_fields.keys():
            self.highlighted += 1
            self.add_field(extra_fields[field])
            self.extra_fields[field] = extra_fields
        self.callback = callback

    def input(self, inkey):
        if inkey.is_sequence and inkey.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(inkey)

    def accept_and_close(self):
        force = self.can_force and self.force_checkbox.checked
        self.callback(force=force, **self.extra_fields)
        self.close()


def format_timedelta(delta):
    hours = int(delta.seconds / 3600)
    minutes = int(delta.seconds / 60) - hours * 60
    seconds = delta.seconds - hours * 3600 - minutes * 60
    if delta.days > 0:
        return "{0}d{1}h ago".format(delta.days, hours)
    elif hours > 0:
        return "{0}h{1}m ago".format(hours, minutes)
    elif minutes > 0:
        return "{0}m{1}s ago".format(minutes, seconds)
    elif seconds > 0:
        return "{0}s ago".format(seconds)
    else:
        return "<1s ago"


def isdumpable(v):
    return not (
        isinstance(v, int)
        or isinstance(v, float)
        or isinstance(v, str)
        or isinstance(v, bool)
    )


class ListResourceDocumentEditor:
    def __init__(
        self,
        provider,
        retrieve_method,
        retrieve_path,
        update_method,
        entry_name_arg,
        update_document_arg,
        entry_key="name",
        entry_name_arg_update=None,
        as_json=True,
        message="Update successful",
    ):
        """
        Initializes a ListResourceDocumentEditor.

            Parameters:
                provider (str): boto3 client provider name
                retrieve_method (str): The method name for the provider to retrieve the document of the edited resource
                retrieve_path (str): Path to the root of the document in the response for the retrieve method
                update_method (str): The method name for the provider to call to update the resource
                entry_name_arg (str): The name of the kwarg for the retrieve_method which must be passed the entry's key.
                update_document_arg (str): The name of the kwarg for the update_method which receives the updated document.
                entry_key (str): The field in the entry which contains the value for the entry name argument.
                entry_name_arg_update (str): The name of the kwarg for the update_method which must be passed the entry's key.
                    If None, use the same as for the retrieve_method.
                as_json (bool): If true, each field is passed as a json object. If false, all list and map fields are converted to their
                    representation via json.dumps before passing. For a ListResourceDocumentEditor, this only affects the root object.
        """
        self.provider = Common.Session.service_provider(provider)
        self.provider_name = provider
        self.retrieve_method = retrieve_method
        if retrieve_method is not None:
            self.retrieve = getattr(self.provider, retrieve_method)
        if update_method is not None:
            self.update = getattr(self.provider, update_method)
        self.retrieve_path = retrieve_path
        self.retrieve_entry_name_arg = entry_name_arg
        self.update_document_arg = update_document_arg
        self.update_entry_name_arg = (
            entry_name_arg_update
            if entry_name_arg_update is not None
            else entry_name_arg
        )
        self.as_json = as_json
        self.update_method = update_method
        self.message = message

    def retrieve_content(self, selection):
        r_kwargs = {self.retrieve_entry_name_arg: self.selection[self.entry_key]}
        response = self.retrieve(**r_kwargs)
        return self.display_content(response)

    def display_content(self, response):
        return json.dumps(
            Common.Session.jq(self.retrieve_path)
            .input(text=json.dumps(response, default=datetime_hack))
            .first(),
            sort_keys=True,
            indent=2,
        )

    def update_content(self, selection, newcontent):
        try:
            u_kwargs = {
                self.update_entry_name_arg: self.selection[self.entry_key],
                self.update_document_arg: json.loads(newcontent)
                if self.as_json
                else newcontent,
            }
            self.update(**u_kwargs)
            Common.success(
                self.message,
                self.update_method,
                self.provider_name.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.update_method,
            )
        except json.JSONDecodeError as e:
            Common.error(
                "JSON decode error: {0}".format(str(e)),
                self.update_method,
                self.provider_name.capitalize(),
                raw=newcontent,
            )
        except botoerror.ClientError as e:
            Common.clienterror(
                e,
                self.update_method,
                self.provider.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.update_method,
            )
        except botoerror.ParamValidationError as e:
            Common.error(
                "Parameter validation error: {0}".format(str(e)),
                self.update_method,
                self.provider.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.update_method,
            )

    def edit(self, selection):
        content = self.retrieve_content(selection)
        newcontent = Common.Session.textedit(content).strip(" \n\t")
        if content == newcontent:
            Common.Session.set_message("Input unchanged.", Common.color("message_info"))
        self.update_content(selection, newcontent)


class ListResourceDocumentCreator(ListResourceDocumentEditor):
    def __init__(
        self,
        provider,
        create_method,
        create_document_arg,
        initial_document=None,
        as_json=True,
        static_fields={},
        message="Create successful",
    ):
        """
        Initializes a ListResourceDocumentCreator.

            Parameters:
                provider (str): boto3 client provider name
                create_method (str): The method name for the provider to call to create the resource
                create_document_arg (str): The name of the kwarg for the create_method which receives the updated document.
                    If empty, the root level object is passed as a set of kwargs.
                initial_document (dict): The initial document to present for editing. Consider it a template of fields to be filled.
                    Expected to be a dict or dict-like structure that can translate to a json string via json.dumps.
        """
        super().__init__(
            provider,
            None,
            ".",
            create_method,
            None,
            create_document_arg,
            entry_key=None,
            entry_name_arg_update=None,
            as_json=as_json,
        )
        self.initial_document = initial_document
        self.golden = self.display_content(self.initial_document)
        self.static_fields = static_fields
        self.create_method = create_method
        self.provider_name = provider
        self.message = message

    def retrieve_content(self, selection):
        from copy import deepcopy

        return self.display_content(deepcopy(self.initial_document))

    def update_content(self, selection, newcontent):
        if newcontent == self.golden:
            Common.Session.set_message("Cancelled", Common.color("message_info"))
            return
        try:
            update_data = json.loads(newcontent)
        except json.JSONDecodeError as e:
            Common.Session.set_message(
                "JSON parse error: {0}".format(e), Common.color("message_error")
            )
            return
        if self.update_document_arg is not None:
            u_kwargs = {
                self.update_document_arg: update_data if self.as_json else newcontent
            }
        else:
            u_kwargs = {}
            for field in update_data.keys():
                if (
                    not isdumpable(update_data[field])
                    or self.as_json is True
                    or (isinstance(self.as_json, list) and field in self.as_json)
                ):
                    u_kwargs[field] = update_data[field]
                else:
                    u_kwargs[field] = json.dumps(
                        update_data[field], default=datetime_hack
                    )
        for field in self.static_fields.keys():
            u_kwargs[field] = self.static_fields[field]
        try:
            self.update(**u_kwargs)
            Common.success(
                self.message,
                self.create_method,
                self.provider_name.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.create_method,
            )
        except botoerror.ClientError as e:
            Common.clienterror(
                e,
                self.create_method,
                self.provider_name.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.create_method,
            )
        except botoerror.ParamValidationError as e:
            Common.error(
                "Parameter validation error: {0}".format(str(e)),
                self.create_method,
                self.provider_name.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.create_method,
            )

    def edit(self, selection=None):
        super().edit(selection)


class ListResourceFieldsEditor(ListResourceDocumentEditor):
    def __init__(
        self,
        provider,
        retrieve_method,
        retrieve_path,
        update_method,
        entry_name_arg,
        fields,
        entry_key="name",
        entry_name_arg_update=None,
        as_json=True,
    ):
        super().__init__(
            provider,
            retrieve_method,
            retrieve_path,
            update_method,
            entry_name_arg,
            None,
            entry_key="name",
            entry_name_arg_update=entry_name_arg_update,
            as_json=as_json,
        )

        self.fields = fields

    def display_content(self, response):
        content = json.dumps(response, default=datetime_hack)
        ret = {}
        for field, path in self.fields.items():
            ret[field] = Common.Session.jq(path).input(text=content).first()
        return json.dumps(ret, sort_keys=True, indent=2)

    def update_content(self, selection, newcontent):
        update_data = json.loads(newcontent)
        u_kwargs = {self.update_entry_name_arg: self.selection[self.entry_key]}
        for field in self.fields.keys():
            if (
                not isdumpable(update_data[field])
                or self.as_json is True
                or (isinstance(self.as_json, list) and field in self.as_json)
            ):
                u_kwargs[field] = update_data[field]
            else:
                u_kwargs[field] = json.dumps(update_data[field], default=datetime_hack)
        try:
            self.update(**u_kwargs)
            Common.Session.set_message(
                "Update successful", Common.color("message_success")
            )
        except botoerror.ClientError as e:
            Common.Session.set_message(
                "AWS API call error: {0}".format(str(e)), Common.color("message_error")
            )
        except botoerror.ParamValidationError as e:
            Common.Session.set_message(
                "Validation error: {0}".format(str(e)), Common.color("message_error")
            )
