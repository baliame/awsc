"""
Module for EC2 instance resources.
"""
import subprocess
from pathlib import Path

from .base_control import (
    Describer,
    DialogFieldResourceListSelector,
    ListResourceDocumentCreator,
    ResourceLister,
    ResourceRefByClass,
    SelectionAttribute,
    SingleRelationLister,
    TemplateDict,
    tagged_column_generator,
)
from .common import Common, SessionAwareDialog
from .termui.control import Border
from .termui.dialog import DialogFieldCheckbox, DialogFieldText
from .termui.ui import ControlCodes


@ResourceLister.Autocommand(
    "EC2ResourceLister", "r", "View related resources", "selection"
)
class EC2RelatedLister(SingleRelationLister):
    """
    Lister control for all resources related to a single EC2 instance based on its description.
    """

    prefix = "ec2_related"
    title = "EC2 Instance related resources"

    resource_type = "ec2 instance"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "Instance"
    describe_method = "describe_instances"
    describe_kwargs = TemplateDict({"InstanceIds": [SelectionAttribute("instance id")]})
    object_path = ".Reservations[0].Instances[0]"
    resource_descriptors = [
        {
            "base_path": "[.SecurityGroups[].GroupId]",
            "type": "Security Group",
            "describer": ResourceRefByClass("SGDescriber"),
        },
        {
            "base_path": '[.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value]',
            "type": "Cloudformation Stack",
            "describer": ResourceRefByClass("CFNDescriber"),
        },
        {
            "base_path": "[.VpcId]",
            "type": "VPC",
            "describer": ResourceRefByClass("VPCDescriber"),
        },
        {
            "base_path": "[.NetworkInterfaces[].NetworkInterfaceId]",
            "type": "Network Interface",
        },
        {
            "base_path": "[.BlockDeviceMappings[].Ebs.VolumeId]",
            "type": "EBS Volume",
            "describer": ResourceRefByClass("EBSDescriber"),
        },
        {
            "base_path": "[.ImageId]",
            "type": "AMI",
            "describer": ResourceRefByClass("AMIDescriber"),
        },
        {
            "base_path": "[.KeyName]",
            "type": "Keypair",
        },
        {
            "base_path": "[.InstanceType]",
            "type": "Instance Type",
            "describer": ResourceRefByClass("InstanceClassDescriber"),
        },
        {
            "base_path": "[.SubnetId]",
            "type": "Subnet",
            "describer": ResourceRefByClass("SubnetDescriber"),
        },
        {
            "base_path": "[.IamInstanceProfile.Arn]",
            "type": "Instance Profile",
            "describer": ResourceRefByClass("InstanceProfileDescriber"),
        },
    ]

    def title_info(self):
        return f"EC2: {self.parent_selection['instance id']}"


@ResourceLister.Autocommand("EBInstanceHealthLister", "v", "View instance")
class EC2Describer(Describer):
    """
    Describer control for EC2 instances.
    """

    prefix = "ec2_browser"
    title = "EC2 Instance"

    def __init__(self, *args, entry_key="instance id", **kwargs):
        self.resource_key = "ec2"
        self.describe_method = "describe_instances"
        self.describe_kwarg_name = "InstanceIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".Reservations[0].Instances[0]"
        super().__init__(*args, entry_key=entry_key, **kwargs)


@ResourceLister.Autocommand("ASGResourceLister", "i", "View instances", "asg")
class EC2ResourceLister(ResourceLister):
    """
    Lister control for EC2 instances.
    """

    prefix = "ec2_list"
    title = "EC2 Instances"
    command_palette = ["ec2", "instance"]

    resource_type = "instance"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "Instance"
    list_method = "describe_instances"
    item_path = "[.Reservations[].Instances[]]"
    columns = {
        "instance id": {
            "path": ".InstanceId",
            "size": 11,
            "weight": 0,
            "sort_weight": 1,
        },
        **tagged_column_generator("name", "name", weight=1, sort_weight=0, size=30),
        "type": {
            "path": ".InstanceType",
            "size": 10,
            "weight": 2,
        },
        "vpc": {
            "path": ".VpcId",
            "size": 15,
            "weight": 3,
        },
        "public ip": {
            "path": ".PublicIpAddress",
            "size": 15,
            "weight": 4,
        },
        "key name": {
            "path": ".KeyName",
            "size": 30,
            "weight": 5,
        },
        "state": {
            "path": ".State.Name",
            "size": 10,
            "weight": 6,
        },
        "image": {"path": ".ImageId", "hidden": True},
    }
    describe_command = EC2Describer.opener
    open_command = "r"
    primary_key = "instance id"

    def title_info(self):
        return self.title_info_data

    def __init__(self, *args, asg=None, **kwargs):
        self.title_info_data = None
        if asg is not None:
            self.list_kwargs = {
                "Filters": [
                    {
                        "Name": "tag:aws:autoscaling:groupName",
                        "Values": [kwargs["asg"]["name"]],
                    }
                ]
            }
            self.title_info_data = f"ASG: {kwargs['asg']['name']}"
        super().__init__(*args, **kwargs)

    @ResourceLister.Autohotkey(ControlCodes.A, "Create AMI", True)
    def create_ami(self, _):
        """
        Hotkey callback for creating an AMI from an instance.
        """
        ListResourceDocumentCreator(
            "ec2",
            "create_image",
            None,
            initial_document={
                "BlockDeviceMappings": [
                    {
                        "DeviceName": "string",
                        "VirtualName": "string",
                        "Ebs": {
                            "DeleteOnTermination": False,
                            "Iops": 123,
                            "SnapshotId": "string",
                            "VolumeSize": 123,
                            "VolumeType": "gp2",
                            "KmsKeyId": "string",
                            "Throughput": 123,
                            "OutpostArn": "string",
                            "Encrypted": False,
                        },
                        "NoDevice": "string",
                    },
                ],
                "Description": "string",
                "Name": "string",
                "NoReboot": True,
                "TagSpecifications": [
                    {
                        "ResourceType": "capacity-reservation",
                        "Tags": [
                            {"Key": "string", "Value": "string"},
                        ],
                    },
                ],
            },
            as_json=["BlockDeviceMappings", "TagSpecifications"],
            static_fields={"InstanceId": self.selection["instance id"]},
        ).edit()

    @ResourceLister.Autohotkey(ControlCodes.S, "Start/stop instance", True)
    def stop_start_instance(self, _):
        """
        Hotkey callback for starting or stopping an instance.
        """
        if self.selection["state"] == "running":
            self.confirm_template(
                "stop_instances",
                TemplateDict(
                    {
                        "InstanceIds": [SelectionAttribute("instance id")],
                    }
                ),
                undoable=True,
                action_name="Stop",
            )(self.selection)
        elif self.selection["state"] == "stopped":
            self.confirm_template(
                "start_instances",
                TemplateDict(
                    {
                        "InstanceIds": [SelectionAttribute("instance id")],
                    }
                ),
                undoable=True,
                action_name="Start",
            )(self.selection)
        else:
            Common.Session.set_message(
                "Instance is not in running or stopped state.",
                Common.color("message_info"),
            )

    @ResourceLister.Autohotkey(ControlCodes.D, "Terminate instance", True)
    def terminate_instance(self, _):
        """
        Hotkey callback for terminating an instance.
        """
        self.confirm_template(
            "terminate_instances",
            TemplateDict(
                {
                    "InstanceIds": [SelectionAttribute("instance id")],
                }
            ),
            undoable=True,
            action_name="Terminate",
        )(self.selection)

    @ResourceLister.Autohotkey("m", "Metrics", True)
    def metrics(self, _):
        """
        Hotkey callback for listing metrics for an EC2 instance.
        """
        Common.Session.push_frame(
            ResourceRefByClass("MetricLister")(
                metric_namespace="AWS/EC2",
                dimension=("InstanceId", self.selection["instance id"]),
            )
        )

    # @ResourceLister.Autohotkey("n", "Launch new instance")
    # def new_instance(self, _):
    #    """
    #    Hotkey callback for launching a new instance.
    #    """
    #    EC2LaunchDialog(
    #        self.parent,
    #        CenterAnchor(0, 0),
    #        Dimension("80%|40", "20"),
    #        caller=self,
    #        weight=-500,
    #    )

    @ResourceLister.Autohotkey("s", "SSH", True)
    def ssh(self, _):
        """
        Hotkey callback for SSHing to an instance.
        """
        key = Common.Session.ssh_key
        keypair_call = Common.generic_api_call(
            "ec2",
            "describe_key_pairs",
            {"KeyNames": self.selection["key name"]},
            "Describe Key Pair",
            "EC2",
            subcategory="Key Pair",
            resource=self.selection["instance id"],
        )
        if keypair_call["Success"]:
            keypair_response = keypair_call["Response"]
            if len(keypair_response["KeyPairs"]) > 0:
                assoc = Common.Session.get_keypair_association(
                    keypair_response["KeyPairs"][0]["KeyPairId"]
                )
                if assoc != "":
                    key = assoc
        path = Path.home() / ".ssh" / key
        if not path.exists():
            Common.Session.set_message(
                "Selected SSH key does not exist", Common.color("message_error")
            )
            return
        if self.selection is not None:
            if self.selection["public ip"] == "":
                Common.Session.set_message(
                    "No public IP associated with instance",
                    Common.color("message_error"),
                )
            else:
                EC2SSHDialog.opener(
                    instance_entry=self.selection,
                    caller=self,
                    weight=-500,
                )


class EC2SSHDialog(SessionAwareDialog):
    """
    Custom dialog for setting SSH parameters and initiating an SSH session to an EC2 instance.
    """

    line_size = 15

    def __init__(
        self,
        *args,
        instance_entry=None,
        caller=None,
        **kwargs,
    ):
        kwargs["border"] = Border(
            Common.border("ec2_ssh", "default"),
            Common.color("ec2_ssh_modal_dialog_border", "modal_dialog_border"),
            "SSH to instance",
            Common.color(
                "ec2_ssh_modal_dialog_border_title", "modal_dialog_border_title"
            ),
            instance_entry["instance id"],
            Common.color(
                "ec2_ssh_modal_dialog_border_title_info",
                "modal_dialog_border_title_info",
            ),
        )
        super().__init__(*args, caller=caller, **kwargs)
        self.set_title_label("Connect to EC2 over SSH")
        self.instance_id = instance_entry["instance id"]
        self.ip = instance_entry["public ip"]
        def_text = (
            Common.Configuration["default_ssh_usernames"][Common.Session.ssh_key]
            if Common.Session.ssh_key in Common.Configuration["default_ssh_usernames"]
            else ""
        )
        self.use_instance_connect = DialogFieldCheckbox(
            "Use EC2 Instance Connect",
            color=Common.color(
                "ec2_ssh_modal_dialog_textfield_label", "modal_dialog_textfield_label"
            ),
            selected_color=Common.color(
                "ec2_ssh_modal_dialog_textfield_selected",
                "modal_dialog_textfield_selected",
            ),
        )
        self.username_textfield = DialogFieldText(
            "SSH username",
            text=def_text,
            **Common.textfield_colors("ec2_ssh"),
        )
        self.add_field(self.use_instance_connect)
        self.add_field(self.username_textfield)
        self.highlighted = 0
        self.caller = caller

    def accept_and_close(self):
        path = Path.home() / ".ssh" / Common.Session.ssh_key
        path_pub = Path.home() / ".ssh" / f"{Common.Session.ssh_key}.pub"
        if self.use_instance_connect:
            if not path_pub.exists():
                Common.Session.set_message(
                    f'Public key "{Common.Session.ssh_key}.pub" does not exist in ~/.ssh',
                    Common.color("message_error"),
                )
            with path_pub.open("r") as file:
                pubkey = file.read()
            api_kwargs = {
                "InstanceId": self.instance_id,
                "InstanceOSUser": self.username_textfield.text,
                "SSHPublicKey": pubkey,
            }
            resp = Common.generic_api_call(
                "ec2-instance-connect",
                "send_ssh_public_key",
                api_kwargs,
                "Instance Connect",
                "EC2",
                subcategory="Instance Connect",
                resource=self.instance_id,
            )
            if not resp["Success"]:
                self.close()
                return
        ssh_cmd = f"{self.username_textfield.text}@{self.ip}"
        Common.info(
            f"SSH to instance: {ssh_cmd}",
            "SSH to instance",
            "EC2",
            resource=self.instance_id,
        )
        exit_code = Common.Session.ui.unraw(
            subprocess.run,
            [
                "bash",
                "-c",
                f"ssh -o StrictHostKeyChecking=no -i {path.resolve()} {ssh_cmd}",
            ],
        )
        Common.Session.set_message(
            f"ssh exited with code {exit_code.returncode}",
            Common.color("message_info"),
        )
        self.close()

    def close(self):
        self.parent.remove_block(self)


@ResourceLister.Autocommand("EC2ResourceLister", "n", "Launch new instance", "_")
class EC2LaunchDialog(SessionAwareDialog):
    """
    Custom dialog for launching a new EC2 instance.
    """

    def __init__(self, parent, alignment, dimensions, *args, caller=None, **kwargs):
        from .resource_ami import AMIResourceLister
        from .resource_ec2_class import InstanceClassResourceLister
        from .resource_keypair import KeyPairResourceLister
        from .resource_sg import SGResourceLister
        from .resource_subnet import SubnetResourceLister

        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            "Launch EC2 instance",
            Common.color("modal_dialog_border_title"),
        )
        super().__init__(parent, alignment, dimensions, caller=caller, *args, **kwargs)
        self.set_title_label("Enter AWS instance details")
        self.name_field = DialogFieldText(
            "Name:",
            label_min=16,
            color=Common.color("modal_dialog_textfield"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
            label_color=Common.color("modal_dialog_textfield_label"),
        )
        self.add_field(self.name_field)
        self.instance_type_field = DialogFieldResourceListSelector(
            InstanceClassResourceLister,
            "Instance type:",
            "t2.micro",
            label_min=16,
            color=Common.color("modal_dialog_textfield"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
            label_color=Common.color("modal_dialog_textfield_label"),
        )
        self.add_field(self.instance_type_field)
        self.image_field = DialogFieldResourceListSelector(
            AMIResourceLister,
            "AMI:",
            "",
            label_min=16,
            color=Common.color("modal_dialog_textfield"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
            label_color=Common.color("modal_dialog_textfield_label"),
        )
        self.add_field(self.image_field)
        self.keypair_field = DialogFieldResourceListSelector(
            KeyPairResourceLister,
            "Keypair:",
            "",
            label_min=16,
            color=Common.color("modal_dialog_textfield"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
            label_color=Common.color("modal_dialog_textfield_label"),
            primary_key="name",
        )
        self.add_field(self.keypair_field)
        self.subnet_field = DialogFieldResourceListSelector(
            SubnetResourceLister,
            "Subnet:",
            "",
            label_min=16,
            color=Common.color("modal_dialog_textfield"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
            label_color=Common.color("modal_dialog_textfield_label"),
        )
        self.add_field(self.subnet_field)
        self.secgroup_field = DialogFieldResourceListSelector(
            SGResourceLister,
            "Security group:",
            "",
            label_min=16,
            color=Common.color("modal_dialog_textfield"),
            selected_color=Common.color("modal_dialog_textfield_selected"),
            label_color=Common.color("modal_dialog_textfield_label"),
        )
        self.add_field(self.secgroup_field)
        self.caller = caller

    def accept_and_close(self):
        if self.name_field.text == "":
            self.error_label.text = "Name cannot be blank."
            return
        if self.instance_type_field.text == "":
            self.error_label.text = "Instance type cannot be blank."
            return
        if self.image_field.text == "":
            self.error_label.text = "AMI cannot be blank."
            return
        if self.keypair_field.text == "":
            self.error_label.text = "Key pair cannot be blank."
            return

        api_kwargs = {
            "ImageId": self.image_field.text,
            "InstanceType": self.instance_type_field.text,
            "KeyName": self.keypair_field.text,
            "MinCount": 1,
            "MaxCount": 1,
            "TagSpecifications": [
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": self.name_field.text}],
                },
            ],
        }
        if self.subnet_field.text != "":
            api_kwargs["SubnetId"] = self.subnet_field.text
            if self.secgroup_field.text != "":
                secgroup_call = Common.generic_api_call(
                    "ec2",
                    "describe_security_groups",
                    {"GroupIds": self.secgroup_field.text},
                    "Describe Security Group",
                    "EC2",
                    subcategory="Security Group",
                    resource=self.secgroup_field.text,
                )
                if not secgroup_call["Success"]:
                    return
                secgroup = secgroup_call["Response"]

                subnet_call = Common.generic_api_call(
                    "ec2",
                    "describe_subnets",
                    {"SubnetIds": self.subnet_field.text},
                    "Describe Subnet",
                    "EC2",
                    subcategory="Subnet",
                    resource=self.subnet_field.text,
                )
                if not subnet_call["Success"]:
                    return
                subnet = subnet_call["Response"]

                if secgroup["VpcId"] == subnet["VpcId"]:
                    api_kwargs["SecurityGroupIds"] = [self.secgroup_field.text]
                else:
                    Common.Session.set_message(
                        "Security group and subnet belong to different VPCs.",
                        Common.color("message_error"),
                    )
                    return
        Common.generic_api_call(
            "ec2",
            "run_instances",
            api_kwargs,
            "Launch Instance",
            "EC2",
            subcategory="Instance",
            success_template="Instance {0} is launching",
        )

        super().accept_and_close()

    def close(self):
        if self.caller is not None:
            self.caller.refresh_data()
        super().close()
