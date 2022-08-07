from pathlib import Path

from .base_control import Describer, GenericDescriber, ResourceLister
from .common import Common
from .termui.list_control import ListEntry
from .termui.ui import ControlCodes


class S3ResourceLister(ResourceLister):
    prefix = "s3_list"
    title = "S3 Buckets"
    command_palette = ["s3"]

    def __init__(self, *args, **kwargs):
        self.resource_key = "s3"
        self.list_method = "list_buckets"
        self.item_path = ".Buckets"
        self.column_paths = {
            "name": ".Name",
            "location": self.determine_location,
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

    def determine_location(self, entry):
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


class S3Describer(Describer):
    prefix = "s3_browser"
    title = "S3 Bucket"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "rds"
        self.describe_method = "get_bucket_policy"
        self.describe_kwarg_name = "Bucket"
        self.object_path = "."
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs,
        )


class CancelDownload(Exception):
    pass


class S3ObjectLister(ResourceLister):
    prefix = "s3_object_list"
    title = "S3 Browser"

    def title_info(self):
        if self.path is None:
            return self.bucket
        else:
            return f"{self.bucket}/{self.path}"

    def __init__(self, *args, bucket, path=None, **kwargs):
        self.icons = {
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

        self.resource_key = "s3"
        self.list_method = "list_objects"
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
        self.item_path = ".Contents + .CommonPrefixes"
        self.column_paths = {
            "icon": self.determine_icon,
            "name": self.determine_name,
            "size": self.determine_size,
        }
        self.hidden_columns = {
            "is_dir": self.determine_is_dir,
            "size_in_bytes": ".Size",
            "bucket_prefixed_path": self.determine_bucket_prefixed_path,
        }
        self.imported_column_sizes = {
            "icon": 1,
            "name": 150,
            "size": 20,
        }
        self.imported_column_order = ["icon", "name", "size"]
        self.sort_column = "name"
        self.additional_commands = {
            "d": {
                "command": self.download_selection,
                "selection_arg": "file",
                "tooltip": "Download",
            },
            "v": {
                "command": self.view_selection,
                "selection_arg": "file",
                "tooltip": "View Contents",
            },
        }
        self.open_command = S3ObjectLister.opener
        self.open_selection_arg = "path"
        super().__init__(*args, **kwargs)
        self.primary_key = "bucket_prefixed_path"
        self.add_hotkey(ControlCodes.D, self.empty, "Cancel download")

    def determine_bucket_prefixed_path(self, entry, *args):
        path = entry["Key"] if "Key" in entry else entry["Prefix"]
        return f"{self.bucket}/{path}"

    def determine_name(self, entry, *args):
        if "Prefix" in entry:
            return entry["Prefix"].strip("/").split("/")[-1]
        return entry["Key"].split("/")[-1]

    def determine_is_dir(self, entry, *args):
        return "/" if "Prefix" in entry else ""

    def determine_size(self, entry, *args):
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

    def determine_icon(self, entry, *args):
        if "Prefix" in entry:
            return self.icons["folder"]
        ext = entry["Key"].split("/")[-1].split(".")[-1]
        ext_key = f"ext.{ext}"
        if ext_key in self.icons:
            return self.icons[ext_key]
        return self.icons["default"]

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
        if self.selection is not None:
            if self.path is None:
                return f"{self.selection['name']}{self.selection['is_dir']}"
            else:
                return f"{self.path}{self.selection['name']}{self.selection['is_dir']}"
        return None

    def get_cache_name(self):
        return f"{self.bucket}/{self.get_selection_path}".replace("/", "--")

    def cache_fetch(self, obj, *args, **kwargs):
        if self.selection is not None:
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
                elif key == ControlCodes.D:
                    raise CancelDownload()
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

            try:
                # TODO: Implement use of libmagic
                with open(obj, "r", encoding="utf-8") as file:
                    return file.read()
            except UnicodeDecodeError:
                with open(obj, "rb") as file:
                    return file.read()

    def download_selection(self, *args, **kwargs):
        if self.selection is not None:
            if self.selection["is_dir"] == "/":
                Common.Session.set_message(
                    "Cannot download directory as file.", Common.color("message_info")
                )
                return
            path = Path.home() / "Downloads" / "awsc"
            path.mkdir(parents=True, exist_ok=True)
            try:
                data = Common.Session.ui.filecache(
                    self.get_cache_name(), self.cache_fetch
                )
            except CancelDownload:
                Common.Session.set_message(
                    "Download cancelled", Common.color("message_info")
                )
                return None
            fpath = path / self.selection["name"]
            # TODO: Implement libmagic
            mode = "w"
            encoding = "utf-8"
            if isinstance(data, bytes):
                mode = "wb"
                encoding = None
            with fpath.open(mode, encoding=encoding) as file:
                file.write(data)
            Common.Session.set_message(
                f"Downloaded file to {fpath.resolve()}",
                Common.color("message_success"),
            )
        return None

    def view_selection(self, *args, **kwargs):
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
            return GenericDescriber.opener(
                **{
                    "describing": f"File: {self.get_selection_path()}",
                    "content": data,
                    "pushed": True,
                }
            )
        return None
