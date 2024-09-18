"""
Module for RDS-related resources.
"""

import json
import subprocess


from .base_control import Describer, DialogFieldResourceListSelector, ResourceLister, tag_finder_generator
from .context import _context_color_defaults
from .common import Common, SessionAwareDialog
from .termui.control import Border
from .termui.dialog import DialogFieldLabel, DialogFieldText


class RDSClusterDescriber(Describer):
    """
    Describer control for RDS database clusters.
    """

    prefix = "rds_browser"
    title = "RDS Cluster"

    resource_type = "database instance"
    main_provider = "rds"
    category = "RDS"
    subcategory = "Database Instance"
    describe_method = "describe_db_clusters"
    describe_kwarg_name = "DBClusterIdentifier"
    object_path = ".DBClusters[0]"
    default_entry_key = "cluster id"


class RDSClusterTunnelDialog(SessionAwareDialog):
    """
    Dialog control for connecting to an SSO.

    Attributes
    ----------
    caller : awsc.termui.control.Control
        Parent control which controls this dialog.
    error_label : awsc.termui.dialog.DialogFieldLabel
        Error label for displaying validation errors.
    name_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the name of the context.
    sso_id_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the SSO ID.
    """

    line_size = 20

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        caller=None,
        cluster=None,
        **kwargs,
    ):
        from .resource_ec2 import EC2ResourceLister

        self.accepts_inputs = True
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            "SSM Tunnel to Cluster",
            Common.color("modal_dialog_border_title"),
        )
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        super().__init__(parent, alignment, dimensions, caller=caller, *args, **kwargs)

        self.info_label = DialogFieldLabel(
            [
                ("Creating an SSH tunnel to an RDS cluster requires an intermediate EC2 jumpbox.", Common.color("generic")),
            ],
            centered=False,
        )
        self.add_field(self.info_label)

        self.instance_selector = DialogFieldResourceListSelector(
            EC2ResourceLister,
            "Jumpbox:",
            default="",
            label_min=16,
            **_context_color_defaults(),
        )
        self.add_field(self.instance_selector)

        def_local_port = ""
        if cluster['engine'] in ["aurora", "aurora-mysql", "mariadb", "mysql"]:
            def_local_port = "3306"
            self.remote_port = 3306
        elif cluster['engine'] in ["aurora-postgresql", "postgres"]:
            def_local_port = "5432"
            self.remote_port = 5432

        self.local_port = DialogFieldText(
            "Local port: ",
            def_local_port,
            label_min=16,
            **_context_color_defaults(),
            accepted_inputs="0123456789",
        )
        
        self.add_field(self.local_port)

        self.cluster = cluster

    def accept_and_close(self):
        if self.instance_selector.value == '':
            self.error_label.text = "Select a valid EC2 instance to continue."
            return
        
        if self.local_port.value == '':
            self.error_label.text = "Local port must be specified."
            return

        self.accepts_inputs = False
        instid = self.instance_selector.value

        instances_call = Common.generic_api_call(
            "ssm",
            "describe_instance_information",
            {"Filters": [{"Key": "InstanceIds", "Values": [instid]}]},
            "Describe instance information",
            "SSM",
            subcategory="SSM Agent",
            resource=instid,
        )
        passed = False
        if instances_call["Success"]:
            instances_response = instances_call["Response"]
            if len(instances_response["InstanceInformationList"]) > 0:
                if instances_response["InstanceInformationList"][0]["PingStatus"] == 'Online':
                    passed = True
        if not passed:
            Common.Session.set_message(
                "Selected instance is not ready to accept SSM connections", Common.color("message_error")
            )
            return
        
        ssm_call = Common.generic_api_call(
            "ssm",
            "start_session",
            {"Target": instid, "DocumentName": "AWS-StartPortForwardingSessionToRemoteHost", "Reason": "AWSC SSH tunnel session", "Parameters": {'host': [self.cluster['endpoint']], "portNumber": [f"{self.remote_port}"], "localPortNumber": [f"{self.local_port.value}"]}},
            "SSM Connect",
            "SSM",
            subcategory="SSM Tunnel",
            resource=instid
        )

        if ssm_call['Success']:
            Common.Session.service_provider.set_env()
            try:
                proc = subprocess.Popen(
                    [
                        "session-manager-plugin",
                        json.dumps(ssm_call['Response']),
                        Common.Session.region,
                        'StartSession',
                        '',
                        json.dumps({"Target": instid}),
                        f'https://ssm.{Common.Session.region}.amazonaws.com'
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )

                Common.Session.add_port_forward(proc, self.cluster['endpoint'], int(self.local_port.value), self.remote_port)
                
                Common.Session.set_message(f"Port forwarding to host {self.cluster['endpoint']}:{self.remote_port} on localhost:{self.local_port.value} active.", Common.color('message_success'))
            except subprocess.CalledProcessError as e:
                if e.returncode != 255:
                    raise
                Common.Session.set_message("SSM session manager plugin (session-manager-plugin) not found in PATH!", Common.color("message_error"))
            finally:
                Common.Session.service_provider.clear_env()
        else:
            Common.Session.set_message("SSM connect to instance failed.", Common.color("message_error"))

        self.close()

class RDSClusterResourceLister(ResourceLister):
    """
    Lister control for RDS database clusters.
    """

    prefix = "rds_cluster_list"
    title = "RDS Clusters"
    command_palette = ["rdscluster", "rdsc"]

    resource_type = "database cluster"
    main_provider = "rds"
    category = "RDS"
    subcategory = "Database Clusters"
    list_method = "describe_db_clusters"
    item_path = ".DBClusters"
    columns = {
        "cluster id": {
            "path": ".DBClusterIdentifier",
            "size": 11,
            "weight": 0,
            "sort_weight": 1,
        },
        "endpoint": {
            "path": ".Endpoint",
            "size": 45,
            "weight": 1,
            "sort_weight": 0,
        },
        "engine": {
            "path": ".Engine",
            "size": 10,
            "weight": 2,
        },
        "mode": {
            "path": ".EngineMode",
            "size": 10,
            "weight": 3,
        },
        "public_access": {"path": ".PubliclyAccessible", "hidden": True},
        "db_name": {"path": ".DatabaseName", "hidden": True},
        "name": {
            "path": tag_finder_generator("Name", taglist_key="TagList"),
            "hidden": True,
        },
    }
    describe_command = RDSClusterDescriber.opener
    primary_key = "cluster id"

    @ResourceLister.Autohotkey("m", "Create SSM tunnel", True)
    def ssm_tunnel(self, _):
        """
        Attempts to create an SSM tunnel to the RDS database through an EC2 instance.
        """
        if self.selection['engine'] not in ["aurora", "aurora-mysql", "mariadb", "mysql", "aurora-postgresql", "postgres"]:
            Common.Session.set_message(f"SSM Tunnel is currently not supported for engine {self.selection['engine']}", Common.color('message_error'))
        RDSClusterTunnelDialog.opener(cluster=self.selection, caller=self)


class RDSDescriber(Describer):
    """
    Describer control for RDS databases.
    """

    prefix = "rds_browser"
    title = "RDS Instance"

    resource_type = "database instance"
    main_provider = "rds"
    category = "RDS"
    subcategory = "Database Instance"
    describe_method = "describe_db_instances"
    describe_kwarg_name = "DBInstanceIdentifier"
    object_path = ".DBInstances[0]"
    default_entry_key = "instance id"    


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
        "db_name": {"path": ".DBName", "hidden": True},
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
