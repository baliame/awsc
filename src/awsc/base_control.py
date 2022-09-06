"""
Module which defines the base controls for awsc. Ideally, all resource specific controls should inherit these and be created with as little
effort as possible.
"""
import datetime
import json
import threading
import traceback
from operator import attrgetter
from typing import Any, Callable, Dict, List, Union

import pyperclip
from botocore import exceptions as botoerror

from .common import (
    Common,
    DefaultAnchor,
    DefaultDimension,
    SessionAwareDialog,
    datetime_hack,
    default_border,
)
from .hotkey import HotkeyDisplay
from .termui.alignment import CenterAnchor, Dimension
from .termui.color import ColorBlackOnGold, ColorBlackOnOrange, ColorGold
from .termui.control import Border
from .termui.dialog import DialogFieldCheckbox, DialogFieldLabel, DialogFieldText
from .termui.list_control import ListControl, ListEntry
from .termui.text_browser import TextBrowser
from .termui.ui import ControlCodes


class RegistryHelper:
    """
    Helper class for control registry.

    Attributes
    ----------
    opener : callable
        Opener function of the control being registered.
    selector : callable
        Selector function of the control being registered.
    """

    def __init__(self, opener=None, selector=None):
        self.opener = opener
        self.selector = selector


def tag_finder_generator(tagname, default="", taglist_key="Tags"):
    """
    Generates a predicate function which can locate a tag in a raw AWS object. Useful if certain important fields are actually just tags.
    I'm looking at you, EC2 instance names.

    Parameters
    ----------
    tagname : str
        The name of the tag to find.
    default : str, default=""
        The default value of the tag, if not found.
    taglist_key : str, default="Tags"
        The name for the list of tags in the object. Believe it or not, this is less than consistent among the AWS services.

    Returns
    -------
    callable(dict-like) -> str
        A function which finds a tag in a dict-like object when called.
    """

    def fn(entry, *args):
        if taglist_key in entry:
            for tag in entry[taglist_key]:
                if tag["Key"] == tagname:
                    return tag["Value"]
        return default

    return fn


def tagged_column_generator(
    name,
    tagname,
    weight=None,
    sort_weight=None,
    hidden=False,
    size=30,
    default="",
    taglist_key="Tags",
):
    """
    Shortcut for generating a field for tag_finder_generator. Eliminates a minor amount of code duplication.

    Parameters
    ----------
    name : str
        The name of the tagged field.
    tagname : str
        The name of the tag to find.
    weight : int, optional
        The weight of the column.
    sort_weight : int, optional
        The weight of the column for sorting.
    size : int, default=30
        The size of the column in characters.
    hidden : bool, default=False
        Is this a hidden column?
    default : str
        The default value if the tag is not found.
    taglist_key : str
        The key for the tag in the JSON document.

    Returns
    -------
    dict
        A dict to insert into the columns map of a ResourceLister.
    """
    ret = {
        name: {
            "path": tag_finder_generator(
                tagname, default=default, taglist_key=taglist_key
            ),
            "hidden": hidden,
        }
    }
    if not hidden:
        if weight is not None:
            ret[name]["weight"] = weight
        ret[name]["size"] = size
    if sort_weight is not None:
        ret[name]["sort_weight"] = sort_weight
    return ret


class StopLoadingData(Exception):
    """
    Custom exception that is thrown when the data fetch thread of a ResourceLister should stop operating.
    """


class OpenableListControl(ListControl):
    """
    A ListControl which is aware of the AWSC session. Implements alternate constructor functions for use in different AWSC-specific contexts.

    Attributes
    ----------
    prefix : str
        The class-specific prefix for the color scheme entries used by this control.
    title : str
        The title of the control to display in the title bar.
    describer : callable
        Callback to call for the default describe action of the control. Describe action will not be automatically generated if this is None.
        In practice, this attribute exists with the expectation that it will point to the opener function of another OpenableListControl or
        GenericDescriber derivative. The current selection of the OpenableListControl is passed in the selection keyword argument.
    selector_cb : callable
        If set, the list control is opened in selector mode. In selector mode, the ENTER hotkey is forcibly replaced with a hotkey that calls
        an external callback passed to the initializer in the selector_cb keyword argument. This exists so we can piggyback existing resource
        listers, such as those for EC2 Instance Classes as a control for selecting from a list of valid values for the value of a dialog field,
        such as a dialog that can be used to create a new EC2 Instance with a specified EC2 Instance Class.
    hotkey_display : awsc.info.HotkeyDisplay
        The hotkey display block associated with this list control. Automatically managed by this control based on its hotkeys. Each control
        is expected to manage its own hotkey display that is then placed in the top right corner of the screen by the session manager.
    """

    prefix = "CHANGEME"
    title = "CHANGEME"
    describer: Union[None, Callable[[], None]] = None

    @classmethod
    def opener(cls, **kwargs):
        """
        Session-aware initializer for this class. Creates an OpenableListControl object with the default alignment settings for the awsc
        layout.

        Returns
        -------
        list(awsc.base_control.OpenableListControl, awsc.info.HotkeyDisplay)
            A new instance of this class, and its associated hotkey display.
        """
        instance = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            **kwargs,
        )
        instance.border = default_border(cls.prefix, cls.title, None)
        return [instance, instance.hotkey_display]

    @classmethod
    def selector(cls, callback, **kwargs):
        """
        Session-aware initializer for this class which opens it in selector mode. Otherwise, functionally identical to the opener classmethod.

        Parameters
        ----------
        callback : callable
            The selector callback.

        Returns
        -------
        list(awsc.base_control.OpenableListControl, awsc.info.HotkeyDisplay)
            A new instance of this class, and its associated hotkey display.
        """
        return cls.opener(**{"selector_cb": callback, **kwargs})

    def __init__(self, *args, selector_cb=None, **kwargs):
        kwargs["color"] = Common.color(f"{self.prefix}_generic", "generic")
        kwargs["selection_color"] = Common.color(
            f"{self.prefix}_selection", "selection"
        )
        kwargs["title_color"] = Common.color(f"{self.prefix}_heading", "column_title")
        super().__init__(*args, **kwargs)
        self.selector_cb = selector_cb
        self.hotkey_display = HotkeyDisplay.opener(caller=self)
        if selector_cb is not None:
            self.add_hotkey("KEY_ENTER", self.select_and_close, "Select and close")
        elif self.describer is not None:
            self.add_hotkey("KEY_ENTER", self.describe, "Describe")
        if self.describer is not None:
            self.add_hotkey("d", self.describe, "Describe")

    def describe(self, _):
        """
        Describe autogenerated action hotkey callback.
        """
        if self.selection is not None and self.describer is not None:
            # pylint: disable=not-callable # Yes it is.
            Common.Session.push_frame(self.describer(selection=self.selection))

    def select_and_close(self, _):
        """
        Select autogenerated action hotkey callback if control is in selector mode.
        """
        if self.selection is not None and self.selector_cb is not None:
            self.selector_cb(self.selection["name"])
            Common.Session.pop_frame()


# TODO: Reimplement resource listers as subclasses of OpenableListControl for consistency.
# TODO: Improve implementation of ResourceListerBase by moving class configuration attributes (eg. primary_key) to class attributes.
class ResourceListerBase(ListControl):
    """
    Base resource lister object. Implements basic concepts about fetching and handling AWS resources as lists.

    Attributes
    ----------
    primary_key : str
        The primary identifying field in each list entry. ListControls display the results of list operations, which will return the primary
        key of each resource in most AWS APIs. We can then use this primary key for get, update and delete operations through different
        controls.
    load_counter : int
        The number of items loaded by the control, for debug purposes.
    dialog_mode : bool
        Indicates whether a modal dialog is present over this ListControl. Having a modal dialog present will prevent automatic refresh
        operations.
    closed : bool
        Flag to indicate whether this control was closed. Used to notify the refresh thread that it should stop refreshing as there is
        no longer any point in doing so.
    next_marker : str
        An AWS next_marker, if paging from the AWS API should continue.
    next_marker_arg : str
        The argument name for the next marker in AWS API calls.
    auto_refresh_last : datetime.datetime
        Represents the last time an automatic refresh happened.
    """

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
        """
        Cleanup hook. Called when the control is closed.
        """
        self.closed = True

    def auto_refresh(self):
        """
        Automatic refresh function stub for implementation in subclasses.
        """

    def asynch(self, fn, *args, clear=False, **kwargs):
        """
        Async wrapper. Starts a data loading thread.

        Parameters
        ----------
        fn : callable
            A function that returns a list of new entries or a generator which yields list entries. This function will be executed in a new
            thread and each entry returned or yielded by this function will be pushed into the new entries cross-thread storage. All
            positional and keyword arguments received in the call to asynch, with the exception of clear, will be passed to this function.
        *args : list
            A list of positional arguments to pass to fn.
        clear : bool, default=False
            If True, request an asynchronous clear of existing list entries in addition to adding new ones.
        **kwargs : dict
            A map of keyword arguments to pass to fn.
        """
        try:
            thread = threading.Thread(
                target=self.async_inner,
                args=args,
                kwargs={**kwargs, "fn": fn, "clear": clear},
                daemon=True,
            )
            thread.start()
        except Exception as error:
            Common.Session.set_message(
                f"Failed to start AWS query thread: {str(error)}",
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
        """
        Inner section of asynch. This function handles the logic of executing the data generator function.

        Parameters
        ----------
        *args : list
            A list of positional arguments to pass to fn.
        fn : callable
            A function that returns a list of new entries or a generator which yields list entries. This function will be executed in this
            thread and each entry returned or yielded by this function will be pushed into the new entries cross-thread storage. All
            positional and keyword arguments received in the call to asynch, with the exception of clear, will be passed to this function.
            The function may raise a StopLoadingData exception to gracefully abort the loading of data.
        clear : bool, default=False
            If True, request an asynchronous clear of existing list entries in addition to adding new ones.
        **kwargs : dict
            A map of keyword arguments to pass to fn.
        """
        try:
            with self.mutex:
                if clear or (
                    not hasattr(self, "primary_key") or self.primary_key is None
                ):
                    self.thread_share["clear"] = True

            for data in fn(*args, **kwargs):
                with self.mutex:
                    self.thread_share["new_entries"].extend(data)

        except StopLoadingData:
            pass
        except Exception as error:  # pylint: disable=broad-except # Purpose of this function is extremely generic, needs a catch-all
            self.thread_share[
                "thread_error"
            ] = f"Refresh thread execution failed: {type(error).__name__}: {str(error)}"
            Common.error(
                f"Refresh thread execution failed: {type(error).__name__}: {str(error)}\n{traceback.format_exc()}",
                "Refresh Thread Error",
                "Core",
                set_message=False,
            )
            Common.Session.set_message(
                "Refresh thread execution failed", Common.color("message_error")
            )
        with self.mutex:
            self.thread_share["updating"] = False
            self.thread_share["finalize"] = True

    def handle_finalization_critical(self):
        """
        Finalization hook. Handles the insertion and sorting of new entries.
        """
        if hasattr(self, "primary_key") and self.primary_key is not None:
            new_entries = []
            for entry in self.entries:
                if entry[self.primary_key] in self.thread_share["acquired"]:
                    new_entries.append(entry)
            self.entries = new_entries[:]
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
        *args,
    ):
        """
        Generic data retrieval function designed to interact with the AWS API.

        Parameters
        ----------
        resource_key : str
            A boto3 provider name.
        list_method : str
            The method to call for acquiring a list of entries within the boto3 provider.
        list_kwargs : dict
            A map of keyword arguments to pass to the method call.
        item_path : str
            Jq expression which, when applied to the json response from the AWS API, results in a json list of entries.
        column_paths : dict
            A mapping of column names to jq expressions. Each expression will be run in the context of a single entry in the list acquired
            by running the item_path jq expression.
        hidden_columns : dict
            Same as column_paths, except these columns are hidden from display.
        next_marker_name : str
            The name of the next marker field in the AWS API response.
        next_marker_arg : str
            The keyword argument for the next marker field for the list method.

        Yields
        ------
        list(ListEntry)
            A list of new entries. The generator yields after each API call the result of that single API call.
        """
        try:
            provider = Common.Session.service_provider(resource_key)
        except KeyError:
            Common.error(
                "boto3 does not recognize provider",
                "Invalid provider",
                "Core",
                subcategory="ResourceListerBase",
                api_provider=resource_key,
                classname=type(self).__name__,
            )
            return []
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
            try:
                response = getattr(provider, list_method)(**it_list_kwargs)
            except botoerror.ClientError as error:
                Common.clienterror(
                    error,
                    "List Resources",
                    "Core",
                    subcategory="ResourceListerBase",
                    api_provider=resource_key,
                    api_method=list_method,
                    api_kwargs=it_list_kwargs,
                )
                # pylint: disable=raise-missing-from # StopLoadingData is a special exception to stop this generator from being used.
                raise StopLoadingData

            items = (
                Common.Session.jq(item_path)
                .input(text=json.dumps(response, default=datetime_hack))
                .first()
            )
            if items is None:
                Common.error(
                    "get_data_generic returned None",
                    "Get Data Generic returned None",
                    "Core",
                    set_message=False,
                    api_provider=resource_key,
                    api_method=list_method,
                    api_kwargs=list_kwargs,
                    item_path=item_path,
                    api_response=response,
                )
                return []

            for item in items:
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
                list_entry = ListEntry(**init)
                list_entry.controller_data = item
                if self.matches(list_entry, *args):
                    ret.append(list_entry)
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
        """
        For pre-filtering resource listers, this function decides whether a list entry being generated matches the criteria for being
        displayed on the control. Used by relational lister subclasses to check for relations.

        Returns
        -------
        bool
            Whether an entry matches the criteria for insertion.
        """
        return True

    def empty(self, _):
        """
        Callback used to generate an empty string. May be unused now.

        Returns
        -------
        str
            An empty string.
        """
        return ""


class DialogFieldResourceListSelector(DialogFieldText):
    """
    A dialog field which allows selecting a single resource in a ResourceLister as the value of the field.

    Attributes
    ----------
    left : int
        How far to the right is the textfield scrolled.
    text : str
        The text in the field. The primary key of the resource will be used for this purpose.
    label : str
        The label of the field.
    color : awsc.termui.color.Color
        The color of the field when not selected.
    label_color : awsc.termui.color.Color
        The color of the field's label.
    selected_color : awsc.termui.color.Color
        The color of the field when it is selected.
    selector_class : object
        An object with a selector method, which takes a callable as an argument and returns a frame list for the session.
        This object will be opened when the user interacts with the field.
    primary_key : str
        If set, overrides the primary key of the selector class.
    """

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
        super().__init__(
            label,
            text=default,
            color=color,
            selected_color=selected_color,
            label_color=label_color,
            label_min=label_min,
            password=False,
            accepted_inputs=None,
        )
        self.selector_class = selector_class
        self.primary_key = primary_key

    def selector_callback(self, entry):
        """
        The callback the lister will call when an entry is selected.

        Parameters
        ----------
        entry : str
            The entry that was selected in the lister.
        """
        self.text = entry

    def input(self, inkey):
        if inkey.is_sequence:
            if inkey.name == "KEY_BACKSPACE":
                inkey.name = "KEY_DELETE"
            if inkey.name in (
                "KEY_LEFT",
                "KEY_RIGHT",
                "KEY_HOME",
                "KEY_END",
                "KEY_DELETE",
            ):
                return super().input(inkey)
            if inkey.name == "KEY_ENTER":
                kwa = {}
                if self.primary_key is not None:
                    kwa["primary_key"] = self.primary_key
                Common.Session.push_frame(
                    self.selector_class.selector(self.selector_callback, **kwa)
                )
                Common.Session.ui.dirty = True
                return True
        return False

    def paint(self, x0, x1, y, selected=False):
        x = x0
        Common.Session.ui.print(self.label, xy=(x, y), color=self.label_color)
        x += max(len(self.label) + 1, self.label_min)
        space = x1 - x + 1
        text = self.text + " ↲"
        if self.left >= len(text):
            self.left = 0
        text = text[
            self.left : (
                self.left + space if len(text) > self.left + space else len(text)
            )
        ]
        Common.Session.ui.print(
            text, xy=(x, y), color=self.selected_color if selected else self.color
        )


# TODO: Create ResourceLister.naming_template for reducing method spam.
class SingleNameDialog(SessionAwareDialog):
    """
    A convenience class for quickly creating a dialog for entering a single string in a textfield.

    Attributes
    ----------
    what : str, default="name"
        The piece of data being entered into the field.
    error_label : awsc.termui.dialog.DialogFieldLabel
        An error label, where validation errors may be displayed.
    name_field : awsc.termui.dialog.DialogFieldText
        The textfield where the name or other data may be typed.
    caller : awsc.termui.control.Control
        The control which opened this dialog.
    callback : callable
        Callback to call when the dialog is confirmed.
    """

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
        **kwargs,
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
        for_part = f" for {subject}" if subject != "" else ""
        self.set_title_label(f"Enter {what}{for_part}")
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
            self.error_label.text = f"You must enter a {self.what}."
            return
        self.callback(self.name_field.text)
        super().accept_and_close()

    def close(self):
        if self.caller is not None:
            self.caller.refresh_data()
        super().close()


class SingleSelectorDialog(SessionAwareDialog):
    """
    A convenience class for quickly creating a dialog for selecting a single resource.

    Attributes
    ----------
    error_label : awsc.termui.dialog.DialogFieldLabel
        An error label, where validation errors may be displayed.
    resource_selector : awsc.base_control.DialogFieldResourceListSelector
        The field that allows selecting a single resource.
    caller : awsc.termui.control.Control
        The control which opened this dialog.
    callback : callable
        Callback to call when the dialog is confirmed.
    """

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        title,
        resource_type,
        action_name,
        selector_class,
        callback,
        *args,
        caller=None,
        **kwargs,
    ):
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            title,
            Common.color("modal_dialog_border_title"),
        )
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            caller=caller,
            **kwargs,
        )
        self.set_title_label(f"Select {resource_type} for {action_name} action")

        if isinstance(selector_class, str):
            # Has a .selector attribute, so it should be fine.
            selector_class = Common.Session.control_registry[selector_class]

        self.resource_selector = DialogFieldResourceListSelector(
            selector_class,
            f"{resource_type}: ",
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


class ForceFlag:
    """
    Represents the value of the force checkbox of a DeleteResourceDialog.
    """

    def resolve(self, selection, **kwargs):
        """
        Resolves the ForceFlag into a value.

        Parameters
        ----------
        selection : termui.list_control.ListEntry
            ForceFlag ignores the selection argument.
        **kwargs: dict, optional
            If this contains an argument named 'force', its value will be used for resolution.

        Returns
        -------
        bool
            Returns the value received in the 'force' keyword argument, or False if it is not present.
        """
        return False if "force" not in kwargs else kwargs["force"]


class FieldValue:
    """
    Represents the value of a field passed as an extra field to a dialog template.

    Attributes
    ----------
    field_name : str
        The name of the field whose value will be used when resolving.
    """

    def __init__(self, field_name):
        """
        Initializes a FieldValue.

        Parameters
        ----------
        field_name : str
            The name of the field whose value will be used when resolving.
        """
        self.field_name = field_name

    def resolve(self, selection, **kwargs):
        """
        Resolves the FieldValue into a value.

        Parameters
        ----------
        selection : termui.list_control.ListEntry
            FieldValue ignores the selection argument.
        **kwargs: dict, optional
            If this contains the field specified in the field_name attribute, its value will be used for resolution.

        Returns
        -------
        any
            The type of the returned value matches the value type of the DialogField specified in field_name. If the field
            is not present in the keyword arguments passed to this function, an empty (None) value is returned.
        """
        return None if self.field_name not in kwargs else kwargs[self.field_name].value


class SelectorTemplateField(FieldValue):
    """
    Convenience class for handling the value of the selection template field.
    """

    def __init__(self):
        super().__init__("value")


class SelectionAttribute:
    """
    Represents a templatable attribute from a ListEntry row.

    Attributes
    ----------
    attribute : str
        The name of the column (attribute) to use from the ListEntry for templating.
    """

    def __init__(self, attribute):
        """
        Initializes a SelectionAttribute.

        Parameters
        ----------
        attribute : str
            The name of the column (attribute) to use from the ListEntry for templating.
        """
        self.attribute = attribute

    def resolve(self, selection, **kwargs):
        """
        Resolves the SelectionAttribute into a value.

        Parameters
        ----------
        selection : termui.list_control.ListEntry
            A ListEntry to use as the row of values for resolving the SelectionAttribute.
        **kwargs: dict, optional
            All other keyword arguments are ignored.

        Returns
        -------
        any
            The type of the returned value matches the type of value stored in the ListEntry. This is ideally,
            but not guaranteed to be a string.
        """
        return selection[self.attribute]


class SelectionControllerDataAttribute:
    """
    Represents a templatable attribute from a ListEntry row's controller data.

    Attributes
    ----------
    attribute : str
        The name of the column (attribute) to use from the ListEntry for templating.
    """

    def __init__(self, attribute):
        """
        Initializes a SelectionControllerDataAttribute.

        Parameters
        ----------
        attribute : str
            The name of the column (attribute) to use from the ListEntry's controller data for templating.
        """
        self.attribute = attribute

    def resolve(self, selection, **kwargs):
        """
        Resolves the SelectionControllerDataAttribute into a value.

        Parameters
        ----------
        selection : termui.list_control.ListEntry
            A ListEntry to use as the row of values for resolving the SelectionControllerDataAttribute.
        **kwargs: dict, optional
            All other keyword arguments are ignored.

        Returns
        -------
        any
            The type of the returned value matches the type of value stored in the ListEntry's controller data.
        """
        return selection.controller_data[self.attribute]


class TemplateList(list):
    """
    A list which can be templated from a ResourceLister control.
    """

    def __init__(self, source=None):
        """
        Initializes a TemplateList.

        Parameters
        ----------
        source : list, optional
            If provided, initializes the TemplateList by recursively converting the provided list.
        """
        super().__init__()
        if source is not None:
            for item in source:
                if isinstance(item, dict):
                    self.append(TemplateDict(item))
                elif isinstance(item, list):
                    self.append(TemplateList(item))
                else:
                    self.append(item)

    def resolve(self, selection, **kwargs):
        """
        Resolves the TemplateList into a list.

        Parameters
        ----------
        selection : termui.list_control.ListEntry
            The selection of a ListControl object to use for resolving SelectionAttribute objects.
        **kwargs : dict, optional
            A list of additional arguments for ForceFlag and FieldValue objects, as passed to the kwargs of
            a DeleteResourceDialog callback.

        Returns
        -------
        list
            A list with the templatable elements recursively resolved to values.
        """
        ret = []
        for item in self:
            if hasattr(item, "resolve"):
                ret.append(item.resolve(selection, **kwargs))
            else:
                ret.append(item)
        return ret


class TemplateDict(dict):
    """
    A dict which can be templated from a ResourceLister control.
    """

    def __init__(self, source=None):
        """
        Initializes a TemplateDict.

        Parameters
        ----------
        source : dict, optional
            If provided, initializes the TemplateDict by recursively converting the provided dict.
        """
        super().__init__()
        if source is not None:
            for key, value in source.items():
                if isinstance(value, dict):
                    self[key] = TemplateDict(value)
                elif isinstance(value, list):
                    self[key] = TemplateList(value)
                else:
                    self[key] = value

    def resolve(self, selection, **kwargs):
        """
        Resolves the TemplateDict into a dict.

        Parameters
        ----------
        selection : termui.list_control.ListEntry
            The selection of a ListControl object to use for resolving SelectionAttribute objects.
        **kwargs : dict, optional
            A list of additional arguments for ForceFlag and FieldValue objects, as passed to the kwargs of
            a DeleteResourceDialog callback.

        Returns
        -------
        dict
            A dict with the templatable elements recursively resolved to values.
        """
        ret = {}
        for key, value in self.items():
            if hasattr(value, "resolve"):
                ret[key] = value.resolve(selection, **kwargs)
            else:
                ret[key] = value
        return ret


class ResourceRefByCommand:
    """
    A ResourceRefByCommand object refers to any openable control which is registered in the Session commander_options by the command.

    Calling an instance of this object is equivalent to calling the opener classmethod of that class.
    """

    def __init__(self, cmd):
        self.cmd = cmd

    def __call__(self, *args, **kwargs):
        return Common.Session.commander_options[self.cmd](*args, **kwargs)


class ResourceRefByClass:
    """
    A ResourceRefByClass object refers to any openable control which is registered in the Session control_registry by class name.

    Calling an instance of this object is equivalent to calling the opener classmethod of that class.
    """

    def __init__(self, cmd):
        self.cmd = cmd

    def __call__(self, *args, **kwargs):
        return Common.Session.control_registry[self.cmd].opener(*args, **kwargs)


class ResourceLister(ResourceListerBase):
    """
    The meaty ResourceLister is the object that handles all of the resource listing from AWS. Most basic resource listers will be direct
    subclasses with minor configuration.

    Attributes
    ----------
    command_palette : list(str)
        A list of commands for opening this particular resource lister. This may be any proper name for the AWS resource, such as `queue`,
        a shorthand, such as `sqs`, or any commonly known alternative name.
    resource_type : str
        The human-readable name of the resource type.
    main_provider : str
        The provider the list_method uses in boto3.
    category : str
        A human-readable name of the category of AWS resources this lister belongs to, for logging purposes.
    subcategory : str
        A human-readable name of the subcategory of AWS resources this lister belongs to, for logging purposes.
    list_method : str
        The method to call to list the resources.
    list_kwargs : dict
        The kwargs to pass to the list method. May be modified in the initializer for dynamic parameters.
    item_path : str
        The path where an item can be retrieved.
    columns : dict
        A map of column specification. Each column's key is the name of the column, while the value is a dict with the following fields:
        - path (required): The jq path for the column within the item.
        - size (required if not hidden): The size of the column.
        - weight (int, default 0): The weight of the column for sorting the columns in order.
        - hidden (bool, default false): Whether the column is hidden.
        - sort_weight (int, optional): If present, the weight of the column for sorting rows. Columns without a sort weight are not used
          for sorting.
    primary_key : str
        The field which contains the unique identifier of the resource. For most resources, this is the same field every time. Not always,
        unfortunately.
    describe_command : callable or str
        The command to run for the describe autogenerated action. If str, this is a reference to another, existing hotkey. If callable, the
        function is called and the return value is pushed as a new frame (so ideally, use an opener classmethod as the thing to pass to this).
        The describe command will be assigned the d hotkey, as well as the ENTER hotkey is no open command is present.
    describe_kwargs : dict
        Additional keyword arguments to pass to the describe command.
    describe_selection_arg : str, default="entry"
        The name of the keyword argument where the selection of this list control should be passed on describe.
    open_command : callable or str
        The command to run for the open autogenerated action. If str, this is a reference to another, existing hotkey. If callable, the
        function is called and the return value is pushed as a new frame (so ideally, use an opener classmethod as the thing to pass to this).
        The open command will be assigned the ENTER hotkey. If not present, the describe_command is instead assigned to the ENTER key.
    open_kwargs : dict
        Additional keyword arguments to pass to the open command.
    open_selection_arg : str, default="entry"
        The name of the keyword argument where the selection of this list control should be passed on open.
    """

    prefix = "CHANGEME"
    title = "CHANGEME"
    command_palette: List[str] = []

    resource_type = "CHANGEME"
    main_provider = "CHANGEME"
    category = "CHANGEME"
    subcategory = "CHANGEME"
    list_method = "CHANGEME"
    list_kwargs: Dict[str, Any] = {}
    item_path = ".ChangeMe"
    columns: Dict[str, Dict[str, Any]] = {}
    primary_key: Union[str, None] = "name"

    describe_selection_arg = "entry"
    describe_command: Union[None, Callable, str] = None
    describe_kwargs: Dict[str, Any] = {}
    open_selection_arg = "entry"
    open_command: Union[None, Callable, str] = None
    open_kwargs: Dict[str, Any] = {}

    additional_commands: Dict[str, Dict[str, Any]] = {}

    class Autocommand:
        """
        Class decorator that automatically assigns a hotkey to a function upon instantiation of the target class.

        This is fuelled by the worst python can offer, I wish you the best of luck in understanding its source.

        Usage: @ResourceLister.Autocommand(command_class, key, tooltip=None, selection_arg=\"entry\", **kwargs)

        Attributes
        ----------
        command_class : str
            The name of the class where the decorated class becomes a command.
        key : str
            The key to press to trigger the command. See HotkeyControl.add_hotkey for more details.
        tooltip : str, optional
            The tooltip to associate with the command. See HotkeyControl.add_hotkey for more details.
        selection_arg : str, default="entry"
            The argument name for passing the selection to the decorated class initializer.
        **kwargs: dict
            A dict of additional keyword arguments to pass to the decorated class initializer.
        """

        _autocommands: Dict[str, Dict[str, Dict[str, Any]]] = {}

        def __init__(
            self, command_class, key, tooltip=None, selection_arg="entry", **kwargs
        ):
            self.command_class = command_class
            self.key = key
            self.tooltip = tooltip
            self.selection_arg = selection_arg
            self.kwargs = kwargs

        def __call__(self, cls):
            if self.command_class not in self.__class__._autocommands:
                self.__class__._autocommands[self.command_class] = {}
            self.__class__._autocommands[self.command_class][self.key] = {
                "command": cls.opener,
                "tooltip": self.tooltip,
                "selection_arg": self.selection_arg,
                "kwargs": self.kwargs,
            }
            return cls

        @classmethod
        def auto_command(cls, self):
            """
            Performs automatically hotkeying up a ResourceLister subclass.

            Inserts all inherited commands automatically. Insertion is done in reverse of MRO - therefore, higher classes on the inheritance tree,
            such as ResourceLister, insert their commands first. This allows subclasses to overwrite these commands.

            Parameters
            ----------
            self : awsc.termui.base_control.ResourceLister
                The class being initialized.
            """
            import inspect

            for classobj in reversed(inspect.getmro(self.__class__)):
                classname = classobj.__name__
                if classname in cls._autocommands:
                    for hotkey, definition in cls._autocommands[classname].items():
                        self.additional_commands[hotkey] = definition

    def autohotkey_condition(self, hotkey):
        return self.selector_cb is None

    def confirm_template(
        self,
        method,
        template,
        custom_callback=None,
        refresh=True,
        category=None,
        subcategory=None,
        provider=None,
        resource_type=None,
        resource_identifier=None,
        undoable=False,
        can_force=False,
        summary=None,
        extra_fields=None,
        action_name="Delete",
        success_template=None,
        hotkey=None,
        hotkey_tooltip=None,
        from_what=None,
        from_what_name=None,
        **kwargs,
    ):
        """
        Creates a confirmation sequence.

        Can be used as a shorthand for registering a confirmation dialog as a hotkey. Returns a function that,
        when called, begins the confirmation process. The returned function requires no arguments, but takes any
        amount for legacy reasons.

        Parameters
        ----------
        method : str
            The name of the method to call for the provider when the action is confirmed.
        template : TemplateDict
            A TemplateDict which describes the keyword arguments to pass to method.
        custom_callback : Callable, optional
            A replacement callback for handling the confirmation.
        refresh : bool, default: True
            Whether to call refresh_data() after executing the action.
        category : str, optional
            API call category, for logging purposes. Usually a pretty printed name for the AWS service that
            is being used. Defaults to the category set on the class.
        subcategory : str, optional
            API call subcategory, for logging purposes. Usually the type of the AWS resource being managed.
            Defaults to the subcategory set on the class.
        provider : str, optional
            The name of the boto3 provider which contains the definition of the method. Defaults to the
            main_provider set on the class.
        resource_type : str, optional
            The name of the type of resource being managed. Defaults to the resource_type set on the class.
        resource_identifier : str, optional
            Templatable via SelectionAttribute. Override for resource identifier if something other than the
            primary key of the current resource should be used.
        undoable : bool, default: False
            Cosmetic, to display a warning about data loss if not set to true.
        can_force : bool, default: False
            Adds an additional force checkbox to the confirmation dialog if set. The value of this checkbox
            is passed as "force" to the callback, and can be represented by a ForceFlag object in the template.
        summary : str, optional
            A short description of the action being performed for logging purposes. Defaults to a concatenation
            of action name and resource type (eg. 'Delete EC2 instance')
        extra_fields : dict, optional
            A map of additional fields to add to the confirmation dialog, where the key is the name of the field,
            and the value is a DialogField instance. These fields are then passed as keyword arguments to the
            callback, where the argument name is the key of the field in the dict. The value of extra fields can
            also be referred to via a FieldValue object in the template.
        action_name : str, default: "Delete"
            The name of the action being performed if the dialog is confirmed. Defaults to 'Delete' as that is both
            the original purpose of confirmation dialogs and the most common action requiring a confirmation.
        success_template : str, optional:
            A formattable string that will be displayed as a message if the operation succeeds. The format method
            will be called on the string, where index 0, and the named field 'resource' will be available as
            arguments containing the resource primary key. All keyword arguments passed to the method will also
            be passed as-is to this invocation of format. Attempts to construct a grammatically correct but not
            particularly pleasing to read message if omitted.
        hotkey : str, optional
            The hotkey for this action. This string should be a valid key for the add_hotkey function. If not
            provided, no hotkey will be added for this confirmation dialog.
        hotkey_tooltip : str, optional
            If set, passes a tooltip for the hotkey to be displayed on the hotkey display list. If omitted, the
            hotkey will be hidden from the hotkey display list.
        from_what : str, optional
            The from_what option of a DeleteResourceDialog.
        from_what_name : str, optional
            Templatable via SelectionAttribute. The from_what_name option of a DeleteResourceDialog.

        Returns
        -------
        callable
            A function that, when called, begins the confirmation process.
        """

        def fn(*args):
            nonlocal category, subcategory, resource_type, provider, summary, extra_fields, success_template

            category = category or self.category
            subcategory = subcategory or self.subcategory
            resource_type = resource_type or self.resource_type
            provider = provider or self.main_provider
            summary = summary or f"{action_name} {resource_type}"
            if extra_fields is None:
                extra_fields = {}
            success_template = (
                success_template
                or f"Performing action '{action_name.lower()} {resource_type}' on resource {'{0}'}..."
            )

            rid = ""
            if resource_identifier is not None:
                rid = resource_identifier
                if hasattr(rid, "resolve") and callable(rid.resolve):
                    # Cannot insert field values at this time.
                    rid = rid.resolve(self.selection, **kwargs)
            elif self.primary_key is not None:
                rid = self.selection[self.primary_key]

            def callback(**cb_kwargs):
                if custom_callback is not None:
                    custom_callback(**cb_kwargs)
                else:
                    Common.generic_api_call(
                        provider,
                        method,
                        template.resolve(self.selection, **kwargs, **cb_kwargs),
                        summary,
                        category,
                        subcategory=subcategory,
                        success_template=success_template,
                        resource=rid,
                        **cb_kwargs,
                    )
                if refresh:
                    self.refresh_data()

            fwn = from_what_name
            if fwn is not None and hasattr(fwn, "resolve") and callable(fwn.resolve):
                # Cannot insert field values at this time.
                fwn = fwn.resolve(self.selection, **kwargs)

            DeleteResourceDialog.opener(
                caller=self,
                resource_type=resource_type,
                resource_identifier=rid,
                callback=callback,
                can_force=can_force,
                extra_fields=extra_fields,
                from_what=from_what,
                from_what_name=fwn,
                **kwargs,
            )

        if hotkey is not None:
            self.add_hotkey(hotkey, fn, hotkey_tooltip, True)
        return fn

    def selector_template(
        self,
        method,
        template,
        title,
        action_name,
        selector_class,
        resource_type=None,
        category=None,
        subcategory=None,
        provider=None,
        summary=None,
        success_template=None,
        caller=None,
        hotkey=None,
        hotkey_tooltip=None,
        hotkey_validated=True,
        refresh=True,
        **kwargs,
    ):
        """
        Templates a SingleSelectionDialog flow, which calls an AWS API method with the provided template at the end of the flow.

        Parameters
        ----------
        method : str
            The name of the method to call for the provider when the action is confirmed.
        template : TemplateDict
            A TemplateDict which describes the keyword arguments to pass to method.
        title : str
            The title for the selection dialog.
        action_name : str
            The action being performed.
        resource_type : str, optional
            The name of the type of resource being managed. Defaults to the resource_type set on the class.
        category : str, optional
            API call category, for logging purposes. Usually a pretty printed name for the AWS service that
            is being used. Defaults to the category set on the class.
        subcategory : str, optional
            API call subcategory, for logging purposes. Usually the type of the AWS resource being managed.
            Defaults to the subcategory set on the class.
        provider : str, optional
            The name of the boto3 provider which contains the definition of the method. Defaults to the
            main_provider set on the class.
        summary : str, optional
            A short description of the action being performed for logging purposes. Defaults to a concatenation
            of action name and resource type (eg. 'Delete EC2 instance')
        success_template : str, optional:
            A formattable string that will be displayed as a message if the operation succeeds. The format method
            will be called on the string, where index 0, and the named field 'resource' will be available as
            arguments containing the resource primary key. All keyword arguments passed to the method will also
            be passed as-is to this invocation of format. Attempts to construct a grammatically correct but not
            particularly pleasing to read message if omitted.
        hotkey : str, optional
            The hotkey for this action. This string should be a valid key for the add_hotkey function. If not
            provided, no hotkey will be added for this confirmation dialog.
        hotkey_tooltip : str, optional
            If set, passes a tooltip for the hotkey to be displayed on the hotkey display list. If omitted, the
            hotkey will be hidden from the hotkey display list.
        hotkey_validated : bool, default=True
            Whether the hotkey to add needs validation.
        refresh : bool, default: True
            Whether to call refresh_data() after executing the action.
        """

        def fn(*args):
            nonlocal category, subcategory, resource_type, provider, summary, success_template

            category = category or self.category
            subcategory = subcategory or self.subcategory
            resource_type = resource_type or self.resource_type
            provider = provider or self.main_provider
            summary = summary or f"{action_name} {resource_type}"
            success_template = (
                success_template
                or f"Performing action '{action_name.lower()} {resource_type}' on resource {'{0}'}..."
            )

            def callback(value):
                cb_kwargs = {"value": value}
                Common.generic_api_call(
                    provider,
                    method,
                    template.resolve(self.selection, **kwargs, **cb_kwargs),
                    summary,
                    category,
                    subcategory=subcategory,
                    success_template=success_template,
                    resource=self.selection[self.primary_key],
                    **cb_kwargs,
                )
                if refresh:
                    self.refresh_data()

            SingleSelectorDialog.opener(
                title,
                resource_type,
                action_name,
                selector_class,
                callback,
                *args,
                caller=self,
                **kwargs,
            )

        if hotkey is not None:
            self.add_hotkey(hotkey, fn, hotkey_tooltip, hotkey_validated)
        return fn

    @classmethod
    def register(cls):
        """
        Classmethod to register this class and all of its subclasses with the commander control.

        Also stores the class in the session control registry for other uses.

        This is why we can reach things via the command palette.
        """
        Common.Session.control_registry[cls.__name__] = RegistryHelper(
            opener=cls.opener, selector=cls.selector
        )
        for cmd in cls.command_palette:
            Common.Session.commander_options[cmd] = cls.opener
        for subcls in cls.__subclasses__():
            subcls.register()

    @classmethod
    def opener(cls, **kwargs):
        """
        Session-aware initializer for this class. Creates an ResourceLister object with the default alignment settings for the awsc
        layout.

        Returns
        -------
        list(awsc.base_control.OpenableListControl, awsc.info.HotkeyDisplay)
            A new instance of this class, and its associated hotkey display.
        """
        instance = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            color=Common.color(f"{cls.prefix}_generic", "generic"),
            selection_color=Common.color(f"{cls.prefix}_selection", "selection"),
            title_color=Common.color(f"{cls.prefix}_heading", "column_title"),
            update_color=Common.color(f"{cls.prefix}_updated", "highlight"),
            update_selection_color=Common.color(
                f"{cls.prefix}_updated", "highlight_selection"
            ),
            **kwargs,
        )
        instance.border = default_border(cls.prefix, cls.title, instance.title_info())
        return [instance, instance.hotkey_display]

    @classmethod
    def selector(cls, callback, **kwargs):
        """
        Session-aware initializer for this class for opening it in selector mode. Otherwise functionally identical to opener().

        Parameters
        ----------
        callback : callable
            The selector callback.

        Returns
        -------
        list(awsc.base_control.OpenableListControl, awsc.info.HotkeyDisplay)
            A new instance of this class, and its associated hotkey display.
        """
        return cls.opener(**{"selector_cb": callback, **kwargs})

    def title_info(self):
        """
        Title info callback for this class. The return value of this shown in the title info dialog.

        Returns
        -------
        str
            The additional info to display in the title of the control.
        """
        return None

    def __init__(self, *args, selector_cb=None, **kwargs):
        super().__init__(*args, **kwargs)
        # resource_key is now main_provider
        ResourceLister.Autocommand.auto_command(self)
        if "list_kwargs" in kwargs:
            self.list_kwargs = kwargs["list_kwargs"]
        if isinstance(self.open_command, str) and (
            not hasattr(self, "additional_commands")
            or self.open_command not in self.additional_commands
        ):
            raise AttributeError(
                "open_command refers to a key that is not in additional_commands"
            )

        if isinstance(self.describe_command, str) and (
            not hasattr(self, "additional_commands")
            or self.describe_command not in self.additional_commands
        ):
            raise AttributeError(
                "describe_command refers to a key that is not in additional_commands"
            )

        self.hidden_columns = {}
        self.column_paths = {}
        self.column_titles = {}
        self.sort_order = []
        self.column_order = []

        for name, spec in self.columns.items():
            if "hidden" in spec and spec["hidden"]:
                self.hidden_columns[name] = spec["path"]
            else:
                self.column_paths[name] = spec["path"]
                self.column_titles[name] = spec["size"]
                self.column_order.append(name)
            if "sort_weight" in spec:
                self.sort_order.append(name)
        self.column_order.sort(
            key=lambda x: self.columns[x]["weight"]
            if "weight" in self.columns[x]
            else 0
        )
        self.sort_order.sort(key=lambda x: self.columns[x]["sort_weight"])

        if "name" not in self.column_paths and "name" not in self.hidden_columns:
            raise AttributeError(
                "name entry is required in column_paths or hidden_columns"
            )

        if "primary_key" in kwargs:
            self.primary_key = kwargs["primary_key"]
        elif not hasattr(self, "primary_key") or self.primary_key is None:
            self.primary_key = "name"

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
        self.hotkey_display = HotkeyDisplay.opener(caller=self)

        self.refresh_data()

    def copy_arn(self, *args):
        """
        Copies the ARN of the selection to the clipboard if available. The ARN is the value of the arn field in the entry.
        Does nothing if the arn field is not present.
        """
        if self.selection is not None:
            pyperclip.copy(self.selection["arn"])
            Common.Session.set_message(
                "Copied resource ARN to clipboard", Common.color("message_success")
            )

    def select_and_close(self, *args):
        """
        Hotkey callback for KEY_ENTER in selector mode. Calls the selector callback and closes the control.
        """
        if (
            self.selection is not None
            and self.selector_cb is not None
            and self.primary_key is not None
        ):
            self.selector_cb(self.selection[self.primary_key])
            Common.Session.pop_frame()

    def command(self, cmd, **kwargs):
        """
        Inner section of a command hotkey callback.
        Commands are hotkeys that open new controls, and therefore require an interaction with the session.

        Commands are automatically loaded from the additional_commands dict.

        Parameters
        ----------
        cmd : callable -> list(awsc.termui.block.Block)
            Callable which returns a display stack frame.
        **kwargs : dict
            A map of additional keyword arguments to pass to cmd.
        """
        if self.selection is not None:
            frame = cmd(**kwargs)
            if frame is not None:
                Common.Session.push_frame(frame)

    def command_wrapper(self, cmd, selection_arg, **kwargs):
        """
        Wraps a command as a hotkey callback.
        Commands are hotkeys that open new controls, and therefore require an interaction with the session.

        Commands are automatically loaded from the additional_commands dict.

        Parameters
        ----------
        cmd : callable -> list(awsc.termui.block.Block)
            Callable which returns a display stack frame.
        selection_arg : str
            The name of the keyword argument where the current selection should be passed to the command.
        **kwargs : dict
            A map of additional keyword arguments to pass to cmd.
        """

        def fn(*args):
            kwargs[selection_arg] = self.selection
            self.command(
                cmd,
                pushed=True,
                caller=self,
                **kwargs,
            )

        return fn

    def describe(self, *args):
        """
        Describe is a special command automatically assigned to 'd' if describe_command is set.

        It is also assigned to ENTER if open_command is not set.
        """
        if self.describe_command is not None:
            self.command_wrapper(
                self.describe_command,
                self.describe_selection_arg,
                **self.describe_kwargs,
            )()

    def open(self, *args):
        """
        Describe is a special command automatically assigned to ENTER if open_command is set.
        """
        if self.open_command is not None:
            self.command_wrapper(self.open_command, self.open_selection_arg)()

    def get_data(self, *args, **kwargs):
        """
        Data streaming function. Yields the return value of get_data_generic one entry at a time.

        Yields
        ------
        awsc.termui.list_control.ListEntry
            A single new entry to add to the list.
        """
        for y in self.get_data_generic(
            self.main_provider,
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
        """
        Performs a full refresh asynchronously, fetching all data again and updating all entries as required.
        """
        with self.mutex:
            if "updating" in self.thread_share and self.thread_share["updating"]:
                return
            self.thread_share["updating"] = True
            self.thread_share["acquired"] = []
        self.auto_refresh_last = datetime.datetime.now()
        self.asynch(self.get_data)

    def sort(self):
        for sort_field in reversed(self.sort_order):
            self.entries.sort(key=attrgetter(sort_field))
        self._cache = None


class NoResults(Exception):
    """
    NoResults is an exception raised by data fetch functions to note that there were no results.
    """


class SingleRelationLister(ResourceListerBase):
    """
    SingleRelationLister parses and lists resources from a single resource's description - such as an EC2 instance. It can be used to display
    a list of resources related to a single resource.

    resource_type : str
        The human-readable name of the resource type.
    main_provider : str
        The provider the describe_method uses in boto3.
    category : str
        A human-readable name of the category of AWS resources this lister belongs to, for logging purposes.
    subcategory : str
        A human-readable name of the subcategory of AWS resources this lister belongs to, for logging purposes.
    describe_method : str
        The method to call to retrieve the single relational resource.
    describe_kwargs : TemplateDict
        The kwargs to pass to the describe method. This is essentially never expected to not depend on an input, so we define it as a
        TemplateDict. At the end of the day, whatever this is is expected to have a resolve() method that takes one positional and two
        keyword arguments and returns a dict. Selection argument received by the __init__ method is passed as the selection, as well as
        all kwargs received as the kwargs.
    object_path : str
        The path where the resource being related is found.
    resource_descriptors : list
        A list of resource specifications. Each resource specification is a dict with the following fields:
        - base_path: The jq path for where the primary keys of this related resource can be found within the resource description.
          The jq expression for base_path must always yield a list of strings.
        - type: The human readable name of the resource type.
        - describer (optional): A callable, usually a ResourceRef or opener function, for the describer of the resource type. Describe
          actions will not be allowed on resources that don't have a describer entry.
    parent_selection : awsc.termui.list_control.ListEntry
        The selection from whatever is opening this. Any dict-like object will do, ListEntry is preferred due to its getattr override.

    """

    prefix = "CHANGEME"
    title = "CHANGEME"

    resource_type = "CHANGEME"
    main_provider = "CHANGEME"
    category = "CHANGEME"
    subcategory = "CHANGEME"
    describe_method = "CHANGEME"
    describe_kwargs: TemplateDict = TemplateDict()
    object_path = ".ChangeMe"
    resource_descriptors: List[Dict[str, Any]] = []

    def title_info(self):
        """
        Title info functions are used to determine the title info after a lister has been instantiated.

        Returns
        -------
        str
            The information in the title.
        """
        return None

    @classmethod
    def opener(cls, **kwargs):
        """
        Session-aware initializer for this class. Creates an SingleRelationLister object with the default alignment settings for the awsc
        layout.

        Returns
        -------
        list(awsc.base_control.SingleRelationLister, awsc.info.HotkeyDisplay)
            A new instance of this class, and its associated hotkey display.
        """
        instance = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            color=Common.color(f"{cls.prefix}_generic", "generic"),
            selection_color=Common.color(f"{cls.prefix}_selection", "selection"),
            title_color=Common.color(f"{cls.prefix}_heading", "column_title"),
            **kwargs,
        )
        instance.border = default_border(cls.prefix, cls.title, instance.title_info())
        return [instance, instance.hotkey_display]

    def __init__(self, parent, alignment, dimensions, *args, selection, **kwargs):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        self.column_order = []
        self.column_titles = {}
        self.parent_selection = selection
        self.describe_kwargs = self.describe_kwargs.resolve(selection, **kwargs)
        self.add_column("type", 30, 0)
        self.add_column("id", 120, 1)
        self.descriptor = None
        self.descriptor_raw = None
        self.add_hotkey("d", self.describe, "Describe", True)
        self.add_hotkey("KEY_ENTER", self.describe, "Describe", True)
        self.hotkey_display = HotkeyDisplay.opener(caller=self)
        self.refresh_data()

    def describe(self, _):
        """
        Describer callback for SingleRelationListers. As these list different datatypes in one control, the specific method to describe the entries is embedded
        in their controller data.
        """
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
        """
        Data retriever callback for SingleRelationListers. Retrieves the resources whose relations are to be discovered and parses each related resource out of
        that description.

        Yields
        ------
        awsc.termui.list_control.ListEntry
            A row to insert.
        """
        if self.descriptor is None:
            try:
                provider = Common.Session.service_provider(self.main_provider)
            except KeyError:
                Common.error(
                    "boto3 does not recognize provider",
                    "Invalid provider",
                    self.category,
                    subcategory=self.subcategory,
                    api_provider=self.main_provider,
                    classname=type(self).__name__,
                    source="SingleRelationLister",
                )
                return
            try:
                resp = getattr(provider, self.describe_method)(**self.describe_kwargs)
            except botoerror.ClientError as error:
                Common.clienterror(
                    error,
                    "Retrieve resource",
                    self.category,
                    subcategory=self.subcategory,
                    api_provider=self.main_provider,
                    api_method=self.describe_method,
                    api_kwargs=self.describe_kwargs,
                    classname=type(self).__name__,
                    source="SingleRelationLister",
                )
                return
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
                    if item is not None
                ]
            except StopIteration:
                continue
            except ValueError:
                continue

    def refresh_data(self, *args, **kwargs):
        """
        Refresher. Initiates an asynchronous data refresh.
        """
        self.asynch(self.get_data, clear=True)

    def sort(self):
        self.entries.sort(key=Common.str_attrgetter("id"))
        self.entries.sort(key=Common.str_attrgetter("type"))
        self._cache = None


class MultiLister(ResourceListerBase):
    """
    A MulitLister is similar to a SingleRelationLister in the ability to list multiple resources in a single control. A MultiLister however acquires this data
    from several different listing API calls rather than from a single resource's description.
    """

    prefix = "CHANGEME"
    title = "CHANGEME"

    def title_info(self):
        """
        Title info functions are used to determine the title info after a lister has been instantiated.

        Returns
        -------
        str
            The information in the title.
        """

        return None

    @classmethod
    def opener(cls, **kwargs):
        """
        Session-aware initializer for this class. Creates an MultiLister object with the default alignment settings for the awsc
        layout.

        Returns
        -------
        list(awsc.base_control.MultiLister, awsc.info.HotkeyDisplay)
            A new instance of this class, and its associated hotkey display.
        """
        instance = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            color=Common.color(f"{cls.prefix}_generic", "generic"),
            selection_color=Common.color(f"{cls.prefix}_selection", "selection"),
            title_color=Common.color(f"{cls.prefix}_heading", "column_title"),
            **kwargs,
        )
        instance.border = default_border(cls.prefix, cls.title, instance.title_info())
        return [instance, instance.hotkey_display]

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        compare_value,
        *args,
        compare_key="id",
        **kwargs,
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        self.add_column("type", 30, 0)
        self.add_column("id", 30, 1)
        if not hasattr(self, "resource_descriptors"):
            self.resource_descriptors = {}
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
        self.hotkey_display = HotkeyDisplay.opener(caller=self)
        self.refresh_data()

    def describe(self, *args):
        """
        Hotkey callback. Opens a generic describer with the data acquired from listing a specific entry as the browsed contents.
        """
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
        """
        Data fetch callback for MultiListers. It's essentially the same as ResourceListers, except this one has several sets of data fetching calls defined.

        Yields
        ------
        awsc.termui.list_control.ListEntry
            A row to insert.
        """
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

    def matches(self, list_entry, *args):
        elem = args[0]
        raw_item = list_entry.controller_data
        if "compare_as_list" not in elem or not elem["compare_as_list"]:
            if callable(elem["compare_path"]):
                val = elem["compare_path"](raw_item)
            else:
                try:
                    val = (
                        Common.Session.jq(elem["compare_path"]).input(raw_item).first()
                    )
                except ValueError:
                    return False
                except StopIteration:
                    return False
            return val == self.compare_value
        if callable(elem["compare_path"]):
            return self.compare_value in elem["compare_path"](raw_item)

        try:
            for val in Common.Session.jq(elem["compare_path"]).input(raw_item).first():
                if val == self.compare_value:
                    return True
        except StopIteration:
            return False
        return False

    def refresh_data(self, *args, **kwargs):
        """
        Refresher. Initiates an asynchronous data refresh.
        """
        self.asynch(self.get_data, clear=True)

    def sort(self):
        self.entries.sort(key=attrgetter("type"))
        self._cache = None


class GenericDescriber(TextBrowser):
    """
    A generic describer control. GenericDescribers make no attempt to contact the AWS API. They're essentially session-aware text browsers.
    """

    prefix = "generic_describer"
    title = "Describe resource"

    @classmethod
    def opener(cls, **kwargs):
        """
        Session-aware initializer for this class. Creates an GenericDescriber object with the default alignment settings for the awsc
        layout.

        Returns
        -------
        list(awsc.base_control.GenericDescriber, awsc.info.HotkeyDisplay)
            A new instance of this class, and its associated hotkey display.
        """
        instance = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            color=Common.color(f"{cls.prefix}_generic", "generic"),
            filtered_color=Common.color(f"{cls.prefix}_filtered", "selection"),
            **kwargs,
        )
        instance.border = default_border(cls.prefix, cls.title, instance.title_info())
        return [instance, instance.hotkey_display]

    def title_info(self):
        """
        Title info functions are used to determine the title info after a lister has been instantiated.

        Returns
        -------
        str
            The information in the title.
        """
        return self.describing

    def __init__(
        self, parent, alignment, dimensions, describing, content, *args, **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        self.describing = describing
        self.add_text(content)
        self.hotkey_display = HotkeyDisplay.opener(caller=self)

    def toggle_wrap(self, *args, **kwargs):
        super().toggle_wrap(*args, **kwargs)
        Common.Session.set_message(
            f"Text wrap {'ON' if self.wrap else 'OFF'}",
            Common.color("message_info"),
        )

    @classmethod
    def register(cls):
        """
        Classmethod to register this class and all of its subclasses with the commander control.

        Also stores the class in the session control registry for other uses.

        This is why we can reach things via the command palette.
        """
        Common.Session.control_registry[cls.__name__] = RegistryHelper(
            opener=cls.opener
        )
        for subcls in cls.__subclasses__():
            subcls.register()


class Describer(TextBrowser):
    """
    Describers are AWS-aware text browsers. When provided with a resource ID, Describer subclasses contact the AWS API on a specified API endpoint, retrieve
    information about the resource, and display it or a subpath (depending on response format) in a syntax-highlighted, pretty-printed JSON form.
    """

    prefix = "CHANGEME"
    title = "CHANGEME"

    @classmethod
    def opener(cls, **kwargs):
        """
        Session-aware initializer for this class. Creates a Describer object with the default alignment settings for the awsc
        layout.

        Returns
        -------
        list(awsc.base_control.Describer, awsc.info.HotkeyDisplay)
            A new instance of this class, and its associated hotkey display.
        """
        instance = cls(
            Common.Session.ui.top_block,
            DefaultAnchor,
            DefaultDimension,
            weight=0,
            color=Common.color(f"{cls.prefix}_generic", "generic"),
            filtered_color=Common.color(f"{cls.prefix}_filtered", "selection"),
            syntax_highlighting=True,
            scheme=Common.Configuration.scheme,
            **kwargs,
        )
        instance.border = default_border(cls.prefix, cls.title, instance.title_info())
        return [instance, instance.hotkey_display]

    def title_info(self):
        """
        Title info functions are used to determine the title info after a lister has been instantiated.

        Returns
        -------
        str
            The information in the title.
        """
        return self.entry_id

    def populate_entry(self, *args, entry, entry_key, **kwargs):
        """
        Populates the entry fields of the Describer based on the entry and entry_key received.

        Expected to be called from the initializer.

        Parameters
        ----------
        entry : awsc.termui.list_control.ListEntry
            The list entry to populate with.
        entry_key : str
            The name of the primary key of the resource.
        """
        if entry is None:
            self.entry = None
            self.entry_id = None
            return
        self.entry = entry
        self.entry_id = entry[entry_key]

    def populate_describe_kwargs(self):
        """
        Populates the describe kwargs dict, which is what will be sent to the AWS API when querying the resource.
        """
        self.describe_kwargs[self.describe_kwarg_name] = (
            [self.entry_id] if self.describe_kwarg_is_list else self.entry_id
        )

    def __init__(
        self, parent, alignment, dimensions, *args, entry, entry_key="name", **kwargs
    ):
        self.populate_entry(entry=entry, entry_key=entry_key)
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        if not hasattr(self, "resource_key"):
            self.resource_key = ""
            raise AttributeError("resource_key is undefined")
        if not hasattr(self, "describe_method"):
            self.describe_method = ""
            raise AttributeError("describe_method is undefined")
        if not hasattr(self, "describe_kwarg_name") and not hasattr(
            self, "describe_kwargs"
        ):
            self.describe_kwarg_name = ""
            raise AttributeError(
                "describe_kwarg_name is undefined and describe_kwargs not set manually"
            )
        if not hasattr(self, "describe_kwarg_is_list"):
            self.describe_kwarg_is_list = False
        if not hasattr(self, "describe_kwargs"):
            self.describe_kwargs = {}
        if not hasattr(self, "object_path"):
            self.object_path = ""
            raise AttributeError("object_path is undefined")
        if hasattr(self, "describe_kwarg_name"):
            self.populate_describe_kwargs()

        self.add_hotkey(ControlCodes.R, self.refresh_data, "Refresh")
        self.hotkey_display = HotkeyDisplay.opener(caller=self)

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

    def command(self, cmd, **kwargs):
        """
        Command caller. See awsc.base_control.ResourceLister.command.
        """
        frame = cmd(**kwargs)
        if frame is not None:
            Common.Session.push_frame(frame)

    def command_wrapper(self, cmd, data_arg, **kwargs):
        """
        Command wrapper. See awsc.base_control.ResourceLister.command_wrapper.
        """

        def fn(*args):
            kwargs[data_arg] = "\n".join(self.lines)
            self.command(
                cmd,
                pushed=True,
                caller=self,
                **kwargs,
            )

        return fn

    def toggle_wrap(self, *args, **kwargs):
        super().toggle_wrap(*args, **kwargs)
        Common.Session.set_message(
            f"Text wrap {'ON' if self.wrap else 'OFF'}",
            Common.color("message_info"),
        )

    def refresh_data(self, *args, **kwargs):
        """
        Data refresh callback. Fetches the info from the AWS API and refreshes the output.
        """
        try:
            provider = Common.Session.service_provider(self.resource_key)
        except KeyError:
            Common.error(
                "boto3 does not recognize provider",
                "Invalid provider",
                "Core",
                subcategory="Describer",
                api_provider=self.resource_key,
                classname=type(self).__name__,
            )
            return
        try:
            response = getattr(provider, self.describe_method)(**self.describe_kwargs)
        except botoerror.ClientError as error:
            Common.clienterror(
                error,
                "List Resources",
                "Core",
                subcategory="Describer",
                api_provider=self.resource_key,
                api_method=self.describe_method,
                api_kwargs=self.describe_kwargs,
            )
            return
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

    @classmethod
    def register(cls):
        """
        Classmethod to register this class and all of its subclasses with the commander control.

        Also stores the class in the session control registry for other uses.

        This is why we can reach things via the command palette.
        """
        Common.Session.control_registry[cls.__name__] = RegistryHelper(
            opener=cls.opener
        )
        for subcls in cls.__subclasses__():
            subcls.register()


class DeleteResourceDialog(SessionAwareDialog):
    """
    Convenience dialog for requesting confirmation for an action. By default, this is tuned for delete actions but really, anything that requires a
    ok or cancel button can be put here.
    """

    def __init__(
        self,
        *args,
        resource_type,
        resource_identifier,
        callback,
        action_name="Delete",
        from_what=None,
        from_what_name=None,
        undoable=False,
        can_force=False,
        extra_fields=None,
        **kwargs,
    ):
        """
        Initializes a DeleteResourceDialog.

        Parameters
        ----------
        resource_type : str, optional
            The name of the type of resource being managed.
        resource_identifier : str, optional
            Identifier for the resource being managed. Does not need to be a primary key, this is for display
            purposes only.
        undoable : bool, default: False
            Cosmetic, to display a warning about data loss if not set to true.
        can_force : bool, default: False
            Adds an additional force checkbox to the confirmation dialog if set.
        extra_fields : dict, optional
            A map of additional fields to add to the confirmation dialog, where the key is the name of the field,
            and the value is a DialogField instance. These fields will be passed keyed by the key to the action callback.
        action_name : str, default: "Delete"
            The name of the action being performed if the dialog is confirmed. Defaults to 'Delete' as that is both
            the original purpose of confirmation dialogs and the most common action requiring a confirmation.
        from_what : str, optional
            If the action is to sever the link between two resources, we can add more context to the label by filling this field.
            This is the type of the other resource in the link if a link is being severed.
        from_what_name : str, optional
            This is the resource identifier for the resource named in from_what.
        """
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            f"{resource_type} {action_name}",
            Common.color("modal_dialog_border_title"),
        )
        super().__init__(*args, **kwargs)
        label = [
            (f"{action_name} ", Common.color("modal_dialog_label")),
            (resource_type, Common.color("modal_dialog_label_highlight")),
            (' resource "', Common.color("modal_dialog_label")),
            (resource_identifier, Common.color("modal_dialog_label_highlight")),
            ('"', Common.color("modal_dialog_label")),
        ]

        if from_what is not None:
            label.append((f" from {from_what}", Common.color("modal_dialog_label")))
            if from_what_name is not None:
                label.append((' "', Common.color("modal_dialog_label")))
                label.append(
                    (from_what_name, Common.color("modal_dialog_label_highlight"))
                )
                label.append(('"', Common.color("modal_dialog_label")))

        label.append(("?", Common.color("modal_dialog_label")))
        self.set_title_label(label)
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
        if extra_fields is not None:
            for field in extra_fields.keys():
                self.highlighted += 1
                self.add_field(extra_fields[field])
                self.extra_fields[field] = extra_fields
        self.callback = callback

    def input(self, key):
        if key.is_sequence and key.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(key)

    def accept_and_close(self):
        force = self.can_force and self.force_checkbox.checked
        self.callback(force=force, **self.extra_fields)
        self.close()


def format_timedelta(delta):
    """
    Timedelta formatter. Outputs a time difference in terms of the two highest time units for which it contains at least one.

    Parameters
    ----------
    delta : datetime.timedelta
        A time delta.

    Returns
    -------
    str
        An "x ago" representation of the delta.
    """
    hours = int(delta.seconds / 3600)
    minutes = int(delta.seconds / 60) - hours * 60
    seconds = delta.seconds - hours * 3600 - minutes * 60
    if delta.days > 0:
        return f"{delta.days}d{hours}h ago"
    if hours > 0:
        return f"{hours}h{minutes}m ago"
    if minutes > 0:
        return f"{minutes}m{seconds}s ago"
    if seconds > 0:
        return f"{seconds}s ago"
    return "<1s ago"


def isdumpable(obj):
    """
    Shorthand for checking if an object is a simple or a complex json type.

    Parameters
    ----------
    obj : object
        Any value.

    Returns
    -------
    bool
        True if obj is not a simple json type (int, float, bool or string).
    """
    return not isinstance(obj, (int, float, str, bool))


class ListResourceDocumentEditor:
    """
    Class for simplifying generating an editor for resources whose body is a JSON document.

    Attributes
    ----------
    provider : object
        Boto3 service provider.
    provider_name : str
        The name of the provider that was passed.
    static_fields : dict
        A mapping of field name to field value for keyword arguments that have a static value in the API call.
    """

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

        Parameters
        ----------
        provider :str
            boto3 client provider name
        retrieve_method : str
            The method name for the provider to retrieve the document of the edited resource
        retrieve_path : str
            Path to the root of the document in the response for the retrieve method
        update_method : str
            The method name for the provider to call to update the resource
        entry_name_arg : str
            The name of the kwarg for the retrieve_method which must be passed the entry's key.
        update_document_arg : str
            The name of the kwarg for the update_method which receives the updated document.
        entry_key : str
            The field in the entry which contains the value for the entry name argument.
        entry_name_arg_update : str
            The name of the kwarg for the update_method which must be passed the entry's key.
            If None, use the same as for the retrieve_method.
        as_json : bool or dict
            If true, each field is passed as a json object. If false, all list and map fields are converted to their
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
        self.entry_key = entry_key
        self.as_json = as_json
        self.update_method = update_method
        self.message = message

    def retrieve_content(self, selection):
        """
        Called when the data for the edited entry is being retrieved.

        Parameters
        ----------
        selection : awsc.termui.list_control.ListEntry
            A ListEntry or dict-like object which contains the primary key of the entry to edit at the set key.

        Returns
        -------
        str
            Return value of display_content on the fetched data.
        """
        r_kwargs = {self.retrieve_entry_name_arg: selection[self.entry_key]}
        response = self.retrieve(**r_kwargs)
        return self.display_content(response)

    def display_content(self, response):
        """
        Creates the display format for the resource retrieved from AWS.

        Parameters
        ----------
        response : dict
            The result of an AWS API call.

        Returns
        -------
        str
            A prettified JSON, which the user will be editing.
        """
        return json.dumps(
            Common.Session.jq(self.retrieve_path)
            .input(text=json.dumps(response, default=datetime_hack))
            .first(),
            sort_keys=True,
            indent=2,
        )

    def update_content(self, selection, newcontent):
        """
        Updates the data on AWS with the data edited by the user.

        Parameters
        ----------
        selection : awsc.termui.list_control.ListEntry
            A ListEntry or dict-like object which contains the primary key of the entry to edit at the set key.
        newcontent : str
            The data as edited by the user.
        """
        try:
            u_kwargs = {
                self.update_entry_name_arg: selection[self.entry_key],
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
        except json.JSONDecodeError as error:
            Common.error(
                f"JSON decode error: {error}",
                self.update_method,
                self.provider_name.capitalize(),
                raw=newcontent,
            )
        except botoerror.ClientError as error:
            Common.clienterror(
                error,
                self.update_method,
                self.provider.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.update_method,
            )
        except botoerror.ParamValidationError as error:
            Common.error(
                f"Parameter validation error: {str(error)}",
                self.update_method,
                self.provider.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.update_method,
            )

    def edit(self, selection):
        """
        Executes the full editing workflow. Retrieves the data from AWS, presents it to the user to edit, then calls back to AWS to update the content.
        """
        content = self.retrieve_content(selection)
        newcontent = Common.Session.textedit(content).strip(" \n\t")
        if content == newcontent:
            Common.Session.set_message("Input unchanged.", Common.color("message_info"))
        self.update_content(selection, newcontent)


class ListResourceDocumentCreator(ListResourceDocumentEditor):
    """
    Class for simplifying generating an editor for resources whose body is a JSON document. This flavour is specifically tuned for create operations.

    Attributes
    ----------
    golden : str
        The initial document in string form. Nothing happens if the state of the document when exiting the editor matches the initial document.
    static_fields : dict
        A mapping of field name to field value for keyword arguments that have a static value in the API call.
    """

    def __init__(
        self,
        provider,
        create_method,
        create_document_arg,
        initial_document=None,
        as_json=True,
        static_fields=None,
        message="Create successful",
    ):
        """
        Initializes a ListResourceDocumentCreator.

        Parameters
        ----------
            provider : str
                boto3 client provider name
            create_method : str
                The method name for the provider to call to create the resource
            create_document_arg : str
                The name of the kwarg for the create_method which receives the updated document.
                If empty, the root level object is passed as a set of kwargs.
            initial_document : dict
                The initial document to present for editing. Consider it a template of fields to be filled.
                Expected to be a dict or dict-like structure that can translate to a json string via json.dumps.
            as_json : bool or list, default=True
                Whether certain fields need to be passed as json or json string. Unfortunately, this is not uniform across
                the AWS APIs. The behaviour is that ints, floats, bools and strings are never changed by this controller.
                Dicts and lists, by default - if this value is True - are dumped as strings. You can disable this behaviour
                by setting this field to False. You can also selectively choose a set of fields where this behaviour should be
                enabled, by setting this to a list of field names. And yes, unfortunately this is a valid use case, there are
                AWS APIs where certain fields are strings of json, while others are json, I'm looking at you, policies.
            static_fields : dict
                A mapping of field name to field value for keyword arguments that have a static value in the API call.
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
            message=message,
        )
        self.initial_document = initial_document
        self.golden = self.display_content(self.initial_document)
        self.static_fields = static_fields if static_fields is not None else {}
        self.create_method = create_method
        self.provider_name = provider

    def retrieve_content(self, selection):
        from copy import deepcopy

        return self.display_content(deepcopy(self.initial_document))

    def generate_kwargs(self, selection, newcontent):
        """
        Generates the kwargs for updating based on the kwargs settings within the object instance.

        Parameters
        ----------
        selection : awsc.termui.list_control.ListEntry
            A ListEntry or dict-like object which contains the primary key of the entry to edit at the set key.
        newcontent : str
            The data as edited by the user.
        """
        update_data = json.loads(newcontent)
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
        return u_kwargs

    def update_content(self, selection, newcontent):
        if newcontent == self.golden:
            Common.Session.set_message("Cancelled", Common.color("message_info"))
            return
        try:
            u_kwargs = self.generate_kwargs(selection, newcontent)
        except json.JSONDecodeError as error:
            Common.Session.set_message(
                f"JSON parse error: {error}", Common.color("message_error")
            )
            return
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
        except botoerror.ClientError as error:
            Common.clienterror(
                error,
                self.create_method,
                self.provider_name.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.create_method,
            )
        except botoerror.ParamValidationError as error:
            Common.error(
                f"Parameter validation error: {str(error)}",
                self.create_method,
                self.provider_name.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.create_method,
            )

    def edit(self, selection=None):
        super().edit(selection)


class ListResourceFieldsEditor(ListResourceDocumentEditor):
    """
    Class for simplifying generating an editor for resources which are essentially just a set of fields. Allows for a more restricted editing session compared
    to ListResourceDocumentEditor.
    """

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
        message="Update successful",
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
            message=message,
        )

        self.fields = fields
        self.orig = {}

    def display_content(self, response):
        content = json.dumps(response, default=datetime_hack)
        ret = {}
        for field, path in self.fields.items():
            ret[field] = Common.Session.jq(path).input(text=content).first()
            self.orig[field] = ret[field]
        return json.dumps(ret, sort_keys=True, indent=2)

    def update_content(self, selection, newcontent):
        update_data = json.loads(newcontent)
        u_kwargs = {self.update_entry_name_arg: selection[self.entry_key]}
        for field in self.fields.keys():
            if self.orig[field] == update_data[field]:
                continue
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
        except botoerror.ClientError as error:
            Common.clienterror(
                error,
                self.update_method,
                self.provider_name.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.update_method,
            )
        except botoerror.ParamValidationError as error:
            Common.error(
                f"Parameter validation error: {str(error)}",
                self.update_method,
                self.provider_name.capitalize(),
                api_kwargs=u_kwargs,
                api_provider=self.provider_name,
                api_method=self.update_method,
            )
