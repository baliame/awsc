"""
Module for S3 resources.
"""
import shutil
from pathlib import Path

from .base_control import Describer, GenericDescriber, ResourceLister
from .common import Common
from .termui.list_control import ListEntry
from .termui.ui import ControlCodes

_s3_icons = {
    "folder": "🗀",
    "default": "🗈",
    "ext.txt": "🖹",
    "ext.png": "🖻",
    "ext.jpg": "🖻",
    "ext.gif": "🖻",
    "ext.jpeg": "🖻",
    "ext.svg": "🖻",
    "ext.doc": "🖺",
    "ext.docx": "🖺",
    "ext.xls": "🖺",
    "ext.xlsx": "🖺",
    "ext.ppt": "🖺",
    "ext.pptx": "🖺",
}


def _s3_object_determine_path(self, entry, *args):
    return entry["Key"] if "Key" in entry else entry["Prefix"]


def _s3_object_determine_name(self, entry, *args):
    if "Prefix" in entry:
        return entry["Prefix"].strip("/").split("/")[-1]
    return entry["Key"].split("/")[-1]


def _s3_object_determine_is_dir(self, entry, *args):
    return "/" if "Prefix" in entry else ""


def _s3_object_determine_size(self, entry, *args):
    if "Prefix" in entry:
        return ""
    b_prefix = ["", "Ki", "Mi", "Gi", "Ti", "Ei"]
    b_idx = 0
    size = float(entry["Size"])
    while size >= 1024:
        b_idx += 1
        size /= 1024
        if b_idx == len(b_prefix) - 1:
            break
    return f"{size:.2f} {b_prefix[b_idx]}B"


def _s3_object_determine_icon(self, entry, *args):
    if "Prefix" in entry:
        return _s3_icons["folder"]
    ext = entry["Key"].split("/")[-1].split(".")[-1]
    ext_key = f"ext.{ext}"
    if ext_key in _s3_icons:
        return _s3_icons[ext_key]
    return _s3_icons["default"]


class S3ObjectLister(ResourceLister):
    """
    Lister control for S3 objects.

    Attributes
    ----------
    bucket : str
        Name of the bucket being browsed.
    path : str
        Initial path within the bucket.
    """

    prefix = "s3_object_list"
    title = "S3 Browser"

    resource_type = "s3 object"
    main_provider = "s3"
    category = "S3"
    subcategory = "Object"
    list_method = "list_objects"
    item_path = ".Contents + .CommonPrefixes"
    columns = {
        "icon": {
            "path": _s3_object_determine_icon,
            "size": 1,
            "weight": 0,
        },
        "name": {
            "path": _s3_object_determine_name,
            "size": 150,
            "weight": 1,
            "sort_weight": 1,
        },
        "gateway": {
            "path": _s3_object_determine_size,
            "size": 30,
            "weight": 2,
        },
        "is_dir": {
            "path": _s3_object_determine_is_dir,
            "hidden": True,
            "sort_weight": 0,
        },
        "size_in_bytes": {
            "path": ".Size",
            "hidden": True,
        },
        "path": {
            "path": _s3_object_determine_path,
            "hidden": True,
        },
    }
    primary_key = "path"

    def title_info(self):
        if self.path is None:
            return self.bucket
        return f"{self.bucket}/{self.path}"

    def __init__(self, *args, bucket, path=None, **kwargs):
        if isinstance(bucket, ListEntry):
            self.bucket = bucket["name"]
        else:
            self.bucket = bucket
        self.path = path
        self.list_kwargs = {"Bucket": self.bucket, "MaxKeys": 100, "Delimiter": "/"}
        self.next_marker = "NextMarker"
        self.next_marker_arg = "Marker"
        if self.path is not None:
            self.list_kwargs["Prefix"] = self.path
        self.open_command = S3ObjectLister.opener
        self.open_selection_arg = "path"
        super().__init__(*args, **kwargs)
        self.add_hotkey(ControlCodes.D, self.empty, "Cancel download")

    def open(self, *args):
        if (
            self.open_command is not None
            and self.selection is not None
            and self.selection["is_dir"] == "/"
        ):
            subpath = self.get_selection_path()
            self.command(
                self.open_command,
                **{
                    self.open_selection_arg: subpath,
                    "bucket": self.bucket,
                    "pushed": True,
                },
            )

    def get_selection_path(self):
        """
        Gets the full path for the current selection within the bucket.

        Returns
        -------
        str
            The full path of the current selection. Has a trailing slash if it's a directory.
        """
        if self.selection is not None:
            if self.path is None:
                return f"{self.selection['name']}{self.selection['is_dir']}"
            return f"{self.path}{self.selection['name']}{self.selection['is_dir']}"
        return None

    def get_cache_name(self):
        """
        Generates a cache name for the currently selected object.

        Returns
        -------
        str
            The cache name for the file.
        """
        return f"{self.bucket}/{self.get_selection_path()}".replace("/", "--")

    def cache_fetch(self, obj, *args, **kwargs):
        """
        Fetches an S3 object to local cache.

        Parameters
        ----------
        obj : str
            The name of the object to fetch.

        Returns
        -------
        str or bytes
            The contents of the file.
        """
        selection_path = self.get_selection_path()
        obj_size = float(self.selection["size_in_bytes"])
        downloaded = 0

        def fn(chunk):
            nonlocal downloaded
            downloaded += chunk
            perc = float(downloaded) / obj_size
            key = Common.Session.ui.check_one_key()
            if key == ControlCodes.C:
                raise KeyboardInterrupt
            if key == ControlCodes.D:
                raise CancelDownload
            Common.Session.ui.progress_bar_paint(perc)

        Common.generic_api_call(
            "s3",
            "download_file",
            {
                "Bucket": self.bucket,
                "Key": selection_path,
                "Filename": obj,
                "Callback": fn,
            },
            "Download File",
            "S3",
            subcategory="Object",
            resource=f"{self.bucket}/{selection_path}",
        )

        return Common.Session.ui.read_file(obj)

    @ResourceLister.Autohotkey("d", "Download", True)
    def download_selection(self, *args, **kwargs):
        """
        Hotkey callback for downloading an S3 object.
        """
        if self.selection["is_dir"] == "/":
            Common.Session.set_message(
                "Cannot download directory as file.", Common.color("message_info")
            )
            return
        path = Path.home() / "Downloads" / "awsc"
        path.mkdir(parents=True, exist_ok=True)
        try:
            objpath = Common.Session.ui.filecache_path(
                self.get_cache_name(), self.cache_fetch
            )
        except CancelDownload:
            Common.Session.set_message(
                "Download cancelled", Common.color("message_info")
            )
            return

        destpath = path / self.selection["name"]
        shutil.copy(objpath, destpath)
        Common.Session.set_message(
            f"Downloaded file to {destpath.resolve()}",
            Common.color("message_success"),
        )

    @ResourceLister.Autohotkey("v", "View", True)
    def view_selection(self, *args, **kwargs):
        """
        Hotkey callback for viewing an S3 object as text.
        """
        if self.selection is not None:
            if self.selection["is_dir"] == "/":
                Common.Session.set_message(
                    "Cannot display directory as text file.",
                    Common.color("message_info"),
                )
                return None
            try:
                data = Common.Session.ui.filecache(
                    self.get_cache_name(), self.cache_fetch
                )
            except CancelDownload:
                Common.Session.set_message(
                    "Download cancelled", Common.color("message_info")
                )
                return None
            if isinstance(data, bytes):
                data = "<binary>"
            Common.Session.push_frame(
                GenericDescriber.opener(
                    **{
                        "describing": f"File: {self.get_selection_path()}",
                        "content": data,
                        "pushed": True,
                    }
                )
            )
        return None


class S3Describer(Describer):
    """
    Describer control for S3 buckets.
    """

    prefix = "s3_browser"
    title = "S3 Bucket"

    def __init__(self, *args, **kwargs):
        self.resource_key = "rds"
        self.describe_method = "get_bucket_policy"
        self.describe_kwarg_name = "Bucket"
        self.object_path = "."
        super().__init__(*args, **kwargs)


def _s3_determine_location(self, entry):
    loc_resps = Common.generic_api_call(
        "s3",
        "get_bucket_location",
        {"Bucket": entry["name"]},
        "Get Bucket Location",
        "S3",
        subcategory="Bucket",
        resource=entry["name"],
    )
    if loc_resps["Success"]:
        loc_resp = loc_resps["Response"]
        return loc_resp["LocationConstraint"]
    return "<n/a>"


class S3ResourceLister(ResourceLister):
    """
    Lister control for S3 buckets.
    """

    prefix = "s3_list"
    title = "S3 Buckets"
    command_palette = ["s3"]

    def __init__(self, *args, **kwargs):
        self.resource_key = "s3"
        self.list_method = "list_buckets"
        self.item_path = ".Buckets"
        self.column_paths = {
            "name": ".Name",
            "location": _s3_determine_location,
        }
        self.imported_column_sizes = {
            "name": 60,
            "location": 20,
        }
        self.describe_command = S3Describer.opener
        self.open_command = S3ObjectLister.opener
        self.open_selection_arg = "bucket"
        self.primary_key = "name"

        self.imported_column_order = ["name", "location"]
        self.sort_column = "name"
        super().__init__(*args, **kwargs)


class CancelDownload(Exception):
    """
    Exception class thrown to abort the ongoing download.
    """
