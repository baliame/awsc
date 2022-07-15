import subprocess

from .base_control import Describer, ResourceLister
from .common import Common, SessionAwareDialog
from .termui.alignment import CenterAnchor, Dimension
from .termui.control import Border
from .termui.dialog import DialogFieldText


class RDSResourceLister(ResourceLister):
    prefix = "rds_list"
    title = "RDS Instances"
    command_palette = ["rds"]

    def title_info(self):
        return self.title_info_data

    def __init__(self, *args, **kwargs):
        self.resource_key = "rds"
        self.list_method = "describe_db_instances"
        self.title_info_data = None
        self.item_path = ".DBInstances"
        self.column_paths = {
            "instance id": ".DBInstanceIdentifier",
            "host": ".Endpoint.Address",
            "engine": ".Engine",
            "type": ".DBInstanceClass",
            "vpc": ".DBSubnetGroup.VpcId",
        }
        self.hidden_columns = {
            "public_access": ".PubliclyAccessible",
            "db_name": ".DBName",
            "name": self.tag_finder_generator("Name", taglist_key="TagList"),
        }
        self.imported_column_sizes = {
            "instance id": 11,
            "host": 45,
            "engine": 10,
            "type": 10,
            "vpc": 15,
        }
        self.describe_command = RDSDescriber.opener
        self.imported_column_order = ["instance id", "host", "engine", "type", "vpc"]
        self.sort_column = "instance id"
        self.primary_key = "instance id"
        super().__init__(*args, **kwargs)
        self.add_hotkey("s", self.db_client, "Open command line")

    def db_client(self, _):
        if self.selection is not None:
            if self.selection["public_access"] != "True":
                Common.Session.set_message(
                    "No public IP associated with instance",
                    Common.color("message_error"),
                )
            else:
                RDSClientDialog(
                    self.parent,
                    CenterAnchor(0, 0),
                    Dimension("80%|40", "10"),
                    instance_entry=self.selection,
                    caller=self,
                    weight=-500,
                )


class RDSDescriber(Describer):
    prefix = "rds_browser"
    title = "RDS Instance"

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        entry,
        *args,
        entry_key="instance id",
        **kwargs
    ):
        self.resource_key = "rds"
        self.describe_method = "describe_db_instances"
        self.describe_kwarg_name = "DBInstanceIdentifier"
        self.object_path = ".DBInstances[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class RDSClientDialog(SessionAwareDialog):
    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        instance_entry=None,
        caller=None,
        *args,
        **kwargs
    ):
        kwargs["border"] = Border(
            Common.border("rds_client_modal", "default"),
            Common.color("rds_client_modal_dialog_border", "modal_dialog_border"),
            "SSH to instance",
            Common.color(
                "rds_client_modal_dialog_border_title", "modal_dialog_border_title"
            ),
            instance_entry["instance id"],
            Common.color(
                "rds_client_modal_dialog_border_title_info",
                "modal_dialog_border_title_info",
            ),
        )
        super().__init__(parent, alignment, dimensions, caller=caller, *args, **kwargs)
        self.instance_id = instance_entry["instance id"]
        self.db_name = instance_entry["db_name"]
        self.ip = instance_entry["host"]
        self.engine = instance_entry["engine"]
        self.username_textfield = DialogFieldText(
            "Username",
            text="",
            color=Common.color(
                "rds_client_modal_dialog_textfield", "modal_dialog_textfield"
            ),
            selected_color=Common.color(
                "rds_client_modal_dialog_textfield_selected",
                "modal_dialog_textfield_selected",
            ),
            label_color=Common.color(
                "rds_client_modal_dialog_textfield_label",
                "modal_dialog_textfield_label",
            ),
            label_min=16,
        )
        self.password_textfield = DialogFieldText(
            "Password",
            text="",
            color=Common.color(
                "rds_client_modal_dialog_textfield", "modal_dialog_textfield"
            ),
            selected_color=Common.color(
                "rds_client_modal_dialog_textfield_selected",
                "modal_dialog_textfield_selected",
            ),
            label_color=Common.color(
                "rds_client_modal_dialog_textfield_label",
                "modal_dialog_textfield_label",
            ),
            label_min=16,
            password=True,
        )
        self.database_textfield = DialogFieldText(
            "Database",
            text=self.db_name,
            color=Common.color(
                "rds_client_modal_dialog_textfield", "modal_dialog_textfield"
            ),
            selected_color=Common.color(
                "rds_client_modal_dialog_textfield_selected",
                "modal_dialog_textfield_selected",
            ),
            label_color=Common.color(
                "rds_client_modal_dialog_textfield_label",
                "modal_dialog_textfield_label",
            ),
            label_min=16,
        )
        self.add_field(self.username_textfield)
        self.add_field(self.password_textfield)
        self.add_field(self.database_textfield)
        self.highlighted = 1 if def_text != "" else 0
        self.caller = caller

    def accept_and_close(self):
        if self.engine in ["aurora", "aurora-mysql", "mariadb", "mysql"]:
            dollar_zero = "mysql"
            cmd = "mysql -h {0} -D {1} -u {2} --password={3}".format(
                self.ip,
                self.database_textfield.text,
                self.username_textfield.text,
                self.password_textfield.text,
            )
        elif self.engine in ["aurora-postgresql", "postgres"]:
            dollar_zero = "psql"
            cmd = "psql postgres://{2}:{3}@{0}/{1}".format(
                self.ip,
                self.database_textfield.text,
                self.username_textfield.text,
                self.password_textfield.text,
            )
        else:
            Common.Session.set_message(
                "Unsupported engine: {0}".format(self.engine),
                Common.color("message_info"),
            )
            self.close()
            return
        ex = Common.Session.ui.unraw(subprocess.run, ["bash", "-c", cmd])
        Common.Session.set_message(
            "{1} exited with code {0}".format(ex.returncode, dollar_zero),
            Common.color("message_info"),
        )
        super().accept_and_close()
