"""
Module for RDS-related resources.
"""
import subprocess

from .base_control import Describer, ResourceLister, tag_finder_generator
from .common import Common, SessionAwareDialog
from .termui.control import Border
from .termui.dialog import DialogFieldText


class RDSDescriber(Describer):
    """
    Describer control for RDS databases.
    """

    prefix = "rds_browser"
    title = "RDS Instance"

    def __init__(self, *args, entry_key="instance id", **kwargs):
        self.resource_key = "rds"
        self.describe_method = "describe_db_instances"
        self.describe_kwarg_name = "DBInstanceIdentifier"
        self.object_path = ".DBInstances[0]"
        super().__init__(*args, entry_key=entry_key, **kwargs)


class RDSResourceLister(ResourceLister):
    """
    Lister control for RDS databases.
    """

    prefix = "rds_list"
    title = "RDS Instances"
    command_palette = ["rds"]

    resource_type = "database instance"
    main_provider = "rds"
    category = "RDS"
    subcategory = "Database Instances"
    list_method = "describe_db_instances"
    item_path = ".DBInstances"
    columns = {
        "instance id": {
            "path": ".DBInstanceIdentifier",
            "size": 11,
            "weight": 0,
            "sort_weight": 1,
        },
        "host": {
            "path": ".Endpoint.Address",
            "size": 45,
            "weight": 1,
            "sort_weight": 0,
        },
        "engine": {
            "path": ".Engine",
            "size": 10,
            "weight": 2,
        },
        "type": {
            "path": ".DBInstanceClass",
            "size": 10,
            "weight": 3,
        },
        "vpc": {
            "path": ".DBSubnetGroup.VpcId",
            "size": 15,
            "weight": 4,
        },
        "public_access": {"path": ".PubliclyAccessible", "hidden": True},
        "db_name": {"path": ".PubliclyAccessible", "hidden": True},
        "name": {
            "path": tag_finder_generator("Name", taglist_key="TagList"),
            "hidden": True,
        },
    }
    describe_command = RDSDescriber.opener
    primary_key = "instance id"

    @ResourceLister.Autohotkey("s", "Open command line", True)
    def db_client(self, _):
        """
        Attempts to open a command line session to connect to the RDS database.
        """
        if self.selection["public_access"] != "True":
            Common.Session.set_message(
                "No public IP associated with instance",
                Common.color("message_error"),
            )
        else:
            RDSClientDialog.opener(instance_entry=self.selection, caller=self)


class RDSClientDialog(SessionAwareDialog):
    """
    Dialog for opening a command line session to connect to the RDS database.

    Attributes
    ----------
    instance_id : str
        The ID of the RDS instance we're connecting to.
    db_name : str
        The name of the default database.
    ip : str
        The hostname of the database.
    username_textfield : awsc.termui.dialog.DialogFieldText
        The username for logging into the database.
    password_textfield : awsc.termui.dialog.DialogFieldText
        The password for logging into the database.
    database_textfield : str
        Optionally, connect to a different database within the instance.
    caller : awsc.termui.control.Control
        The parent control controlling this dialog.
    """

    line_size = 15

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        instance_entry=None,
        caller=None,
        **kwargs,
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
        super().__init__(parent, alignment, dimensions, *args, caller=caller, **kwargs)
        self.instance_id = instance_entry["instance id"]
        self.db_name = instance_entry["db_name"]
        self.ip = instance_entry["host"]
        self.engine = instance_entry["engine"]
        self.set_title_label("Connect to RDS instance")
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
        # self.highlighted = 1 if def_text != "" else 0
        self.caller = caller

    def accept_and_close(self):
        if self.engine in ["aurora", "aurora-mysql", "mariadb", "mysql"]:
            dollar_zero = "mysql"
            cmd = f"mysql -h {self.ip} -D {self.database_textfield.text} -u {self.username_textfield.text} --password={self.password_textfield.text}"
        elif self.engine in ["aurora-postgresql", "postgres"]:
            dollar_zero = "psql"
            cmd = f"psql postgres://{self.username_textfield}:{self.password_textfield}@{self.ip}/{self.database_textfield}"
        else:
            Common.Session.set_message(
                f"Unsupported engine: {self.engine}",
                Common.color("message_info"),
            )
            self.close()
            return
        exit_code = Common.Session.ui.unraw(subprocess.run, ["bash", "-c", cmd])
        Common.Session.set_message(
            f"{dollar_zero} exited with code {exit_code.returncode}",
            Common.color("message_info"),
        )
        super().accept_and_close()
