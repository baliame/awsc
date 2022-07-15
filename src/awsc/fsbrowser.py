from pathlib import Path

from .base_control import GenericDescriber
from .common import Common
from .termui.list_control import ListControl, ListEntry
from .termui.ui import ControlCodes


class FSBrowser(ListControl):
    prefix = "fs_list"
    title = "S3 Browser"

    def title_info(self):
        if self.path is None:
            return self.bucket
        else:
            return "{0}/{1}".format(self.bucket, self.path)

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
        return "{0}/{1}".format(
            self.bucket, entry["Key"] if "Key" in entry else entry["Prefix"]
        )

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
        s = float(entry["Size"])
        while s >= 1024:
            b_idx += 1
            s /= 1024
            if b_idx == len(b_prefix) - 1:
                break
        return "{0:.2f} {1}B".format(s, b_prefix[b_idx])

    def determine_icon(self, entry, *args):
        if "Prefix" in entry:
            return self.icons["folder"]
        ext = entry["Key"].split("/")[-1].split(".")[-1]
        ext_key = "ext.{0}".format(ext)
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
                {
                    self.open_selection_arg: subpath,
                    "bucket": self.bucket,
                    "pushed": True,
                },
            )

    def get_selection_path(self):
        if self.selection is not None:
            if self.path is None:
                return "{0}{1}".format(self.selection["name"], self.selection["is_dir"])
            else:
                return "{0}{1}{2}".format(
                    self.path, self.selection["name"], self.selection["is_dir"]
                )
        return None

    def get_cache_name(self):
        return "{0}/{1}".format(self.bucket, self.get_selection_path()).replace(
            "/", "--"
        )

    def cache_fetch(self, obj, *args, **kwargs):
        if self.selection is not None:
            sp = self.get_selection_path()
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

            Common.Session.service_provider("s3").download_file(
                Bucket=self.bucket, Key=sp, Filename=obj, Callback=fn
            )
            try:
                with open(obj, "r") as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(obj, "rb") as f:
                    return f.read()

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
            mode = "w"
            if isinstance(data, bytes):
                mode = "wb"
            with fpath.open(mode) as f:
                f.write(data)
            Common.Session.set_message(
                "Downloaded file to {0}".format(str(fpath.resolve())),
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
                    "describing": "File: {0}".format(self.get_selection_path()),
                    "content": data,
                    "pushed": True,
                }
            )
        return None
