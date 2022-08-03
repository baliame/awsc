import subprocess
from pathlib import Path

from .base_control import (
    DeleteResourceDialog,
    Describer,
    DialogFieldResourceListSelector,
    ListResourceDocumentCreator,
    ResourceLister,
    SingleNameDialog,
    SingleRelationLister,
)
from .common import Common, SessionAwareDialog
from .termui.alignment import CenterAnchor, Dimension
from .termui.control import Border
from .termui.dialog import DialogFieldCheckbox, DialogFieldLabel, DialogFieldText
from .termui.ui import ControlCodes


class EC2RelatedLister(SingleRelationLister):
    prefix = "ec2_related"
    title = "EC2 Instance related resources"

    def title_info(self):
        return self.instance_id

    def __init__(self, *args, ec2_entry=None, **kwargs):
        from .resource_ami import AMIDescriber
        from .resource_cfn import CFNDescriber
        from .resource_ebs import EBSDescriber
        from .resource_ec2_class import InstanceClassDescriber
        from .resource_iam import InstanceProfileDescriber
        from .resource_sg import SGDescriber
        from .resource_subnet import SubnetDescriber
        from .resource_vpc import VPCDescriber

        self.resource_key = "ec2"
        self.instance_id = ec2_entry["instance id"]
        self.describe_method = "describe_instances"
        self.describe_kwargs = {"InstanceIds": [self.instance_id]}
        self.object_path = ".Reservations[0].Instances[0]"
        self.resource_descriptors = [
            {
                "base_path": "[.SecurityGroups[].GroupId]",
                "type": "Security Group",
                "describer": SGDescriber.opener,
            },
            {
                "base_path": '[.Tags[] | select(.Key=="aws:cloudformation:stack-id").Value]',
                "type": "Cloudformation Stack",
                "describer": CFNDescriber.opener,
            },
            {
                "base_path": "[.VpcId]",
                "type": "VPC",
                "describer": VPCDescriber.opener,
            },
            {
                "base_path": "[.NetworkInterfaces[].NetworkInterfaceId]",
                "type": "Network Interface",
            },
            {
                "base_path": "[.BlockDeviceMappings[].Ebs.VolumeId]",
                "type": "EBS Volume",
                "describer": EBSDescriber.opener,
            },
            {
                "base_path": "[.ImageId]",
                "type": "AMI",
                "describer": AMIDescriber.opener,
            },
            {
                "base_path": "[.KeyName]",
                "type": "Keypair",
            },
            {
                "base_path": "[.InstanceType]",
                "type": "Instance Type",
                "describer": InstanceClassDescriber.opener,
            },
            {
                "base_path": "[.SubnetId]",
                "type": "Subnet",
                "describer": SubnetDescriber.opener,
            },
            {
                "base_path": "[.IamInstanceProfile.Arn]",
                "type": "Instance Profile",
                "describer": InstanceProfileDescriber.opener,
            },
        ]
        super().__init__(*args, **kwargs)


class EC2ResourceLister(ResourceLister):
    prefix = "ec2_list"
    title = "EC2 Instances"
    command_palette = ["ec2", "instance"]

    def title_info(self):
        return self.title_info_data

    def __init__(self, *args, **kwargs):
        self.resource_key = "ec2"
        self.list_method = "describe_instances"
        self.title_info_data = None
        if "asg" in kwargs:
            self.list_kwargs = {
                "Filters": [
                    {
                        "Name": "tag:aws:autoscaling:groupName",
                        "Values": [kwargs["asg"]["name"]],
                    }
                ]
            }
            self.title_info_data = "ASG: {0}".format(kwargs["asg"]["name"])
        self.item_path = "[.Reservations[].Instances[]]"
        self.column_paths = {
            "instance id": ".InstanceId",
            "name": self.tag_finder_generator("Name"),
            "type": ".InstanceType",
            "vpc": ".VpcId",
            "public ip": ".PublicIpAddress",
            "key name": ".KeyName",
            "state": ".State.Name",
        }
        self.imported_column_sizes = {
            "instance id": 11,
            "name": 30,
            "type": 10,
            "vpc": 15,
            "public ip": 15,
            "key name": 30,
            "state": 10,
        }
        self.hidden_columns = {"image": ".ImageId"}
        self.describe_command = EC2Describer.opener
        self.imported_column_order = [
            "instance id",
            "name",
            "type",
            "vpc",
            "public ip",
            "key name",
            "state",
        ]
        self.sort_column = "instance id"
        self.primary_key = "instance id"
        super().__init__(*args, **kwargs)
        self.add_hotkey("s", self.ssh, "Open SSH")
        self.add_hotkey("l", self.new_instance, "Launch new instance")
        self.add_hotkey("m", self.metrics, "Metrics")
        self.add_hotkey("r", self.related, "View related resources")
        self.add_hotkey(ControlCodes.A, self.create_ami, "Create AMI from instance")
        self.add_hotkey(ControlCodes.S, self.stop_start_instance, "Stop/start instance")
        self.add_hotkey(ControlCodes.D, self.terminate_instance, "Terminate instance")

    def create_ami(self, _):
        if self.selection is None:
            return
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

    def stop_start_instance(self, _):
        if self.selection is not None:
            if self.selection["state"] == "running":
                DeleteResourceDialog(
                    self.parent,
                    CenterAnchor(0, 0),
                    Dimension("80%|40", "10"),
                    caller=self,
                    resource_type="EC2 Instance",
                    resource_identifier=self.selection["instance id"],
                    callback=self.do_stop,
                    undoable=True,
                    action_name="Stop",
                )
            elif self.selection["state"] == "stopped":
                DeleteResourceDialog(
                    self.parent,
                    CenterAnchor(0, 0),
                    Dimension("80%|40", "10"),
                    caller=self,
                    resource_type="EC2 Instance",
                    resource_identifier=self.selection["instance id"],
                    callback=self.do_start,
                    undoable=True,
                    action_name="Start",
                )
            else:
                Common.Session.set_message(
                    "Instance is not in running or stopped state.",
                    Common.color("message_info"),
                )

    def terminate_instance(self, _):
        if self.selection is not None:
            DeleteResourceDialog(
                self.parent,
                CenterAnchor(0, 0),
                Dimension("80%|40", "10"),
                caller=self,
                resource_type="EC2 Instance",
                resource_identifier=self.selection["instance id"],
                callback=self.do_terminate,
                action_name="Terminate",
            )

    def metrics(self, _):
        from .resource_cloudwatch import MetricLister

        if self.selection is not None:
            Common.Session.push_frame(
                MetricLister.opener(
                    metric_namespace="AWS/EC2",
                    dimension=("InstanceId", self.selection["instance id"]),
                )
            )

    def related(self, _):
        if self.selection is not None:
            Common.Session.push_frame(EC2RelatedLister.opener(ec2_entry=self.selection))

    def do_start(self, **kwargs):
        if self.selection is None:
            return
        api_kwargs = {
            "InstanceIds": [self.selection["instance id"]],
        }
        Common.generic_api_call(
            "ec2",
            "start_instances",
            api_kwargs,
            "Start instance",
            "EC2",
            subcategory="Instance",
            success_template="Starting instance {0}",
            resource=self.selection["instance id"],
        )
        self.refresh_data()

    def do_stop(self, **kwargs):
        if self.selection is None:
            return
        api_kwargs = {
            "InstanceIds": [self.selection["instance id"]],
        }
        Common.generic_api_call(
            "ec2",
            "stop_instances",
            api_kwargs,
            "Stop instance",
            "EC2",
            subcategory="Instance",
            success_template="Stopping instance {0}",
            resource=self.selection["instance id"],
        )
        self.refresh_data()

    def do_terminate(self, **kwargs):
        if self.selection is None:
            return
        api_kwargs = {
            "InstanceIds": [self.selection["instance id"]],
        }
        Common.generic_api_call(
            "ec2",
            "terminate_instances",
            api_kwargs,
            "Terminate instance",
            "EC2",
            subcategory="Instance",
            success_template="Terminating instance {0}",
            resource=self.selection["instance id"],
        )
        self.refresh_data()

    def new_instance(self, _):
        EC2LaunchDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "20"),
            caller=self,
            weight=-500,
        )

    def ssh(self, _):
        if self.selection is None:
            return
        key = Common.Session.ssh_key
        kpr = Common.generic_api_call(
            "ec2",
            "describe_key_pairs",
            {"KeyNames": self.selection["key name"]},
            "Describe Key Pair",
            "EC2",
            subcategory="Key Pair",
            resource=self.selection["instance id"],
        )
        if kpr["Success"]:
            kp = kpr["Response"]
            if len(kp["KeyPairs"]) > 0:
                assoc = Common.Session.get_keypair_association(
                    kp["KeyPairs"][0]["KeyPairId"]
                )
                if assoc != "":
                    key = assoc
        p = Path.home() / ".ssh" / key
        if not p.exists():
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
                EC2SSHDialog(
                    self.parent,
                    CenterAnchor(0, 0),
                    Dimension("80%|40", "10"),
                    instance_entry=self.selection,
                    caller=self,
                    weight=-500,
                )


class EC2Describer(Describer):
    prefix = "ec2_browser"
    title = "EC2 Instance"

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
        self.resource_key = "ec2"
        self.describe_method = "describe_instances"
        self.describe_kwarg_name = "InstanceIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".Reservations[0].Instances[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class EC2SSHDialog(SessionAwareDialog):
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
        super().__init__(parent, alignment, dimensions, caller=caller, *args, **kwargs)
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
            color=Common.color(
                "ec2_ssh_modal_dialog_textfield", "modal_dialog_textfield"
            ),
            selected_color=Common.color(
                "ec2_ssh_modal_dialog_textfield_selected",
                "modal_dialog_textfield_selected",
            ),
            label_color=Common.color(
                "ec2_ssh_modal_dialog_textfield_label", "modal_dialog_textfield_label"
            ),
            label_min=16,
        )
        self.add_field(self.use_instance_connect)
        self.add_field(self.username_textfield)
        self.highlighted = 0
        self.caller = caller

    def accept_and_close(self):
        ph = Path.home() / ".ssh" / Common.Session.ssh_key
        ph_pub = Path.home() / ".ssh" / "{0}.pub".format(Common.Session.ssh_key)
        if self.use_instance_connect:
            if not ph_pub.exists():
                Common.Session.set_message(
                    'Public key "{0}.pub" does not exist in ~/.ssh'.format(
                        Common.Session.ssh_key
                    ),
                    Common.color("message_error"),
                )
            with ph_pub.open("r") as f:
                pubkey = f.read()
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
        ssh_cmd = "{0}@{1}".format(self.username_textfield.text, self.ip)
        Common.info(
            "SSH to instance: {0}".format(self.ssh_cmd),
            "SSH to instance",
            "EC2",
            resource=self.instance_id,
        )
        ex = Common.Session.ui.unraw(
            subprocess.run,
            [
                "bash",
                "-c",
                "ssh -o StrictHostKeyChecking=no -i {0} {1}".format(
                    str(ph.resolve()), ssh_cmd
                ),
            ],
        )
        Common.Session.set_message(
            "ssh exited with code {0}".format(ex.returncode),
            Common.color("message_info"),
        )
        self.close()

    def close(self):
        self.parent.remove_block(self)


class EC2LaunchDialog(SessionAwareDialog):
    def __init__(self, parent, alignment, dimensions, caller=None, *args, **kwargs):
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
        self.add_field(DialogFieldLabel("Enter AWS instance details"))
        self.error_label = DialogFieldLabel(
            "", default_color=Common.color("modal_dialog_error")
        )
        self.add_field(self.error_label)
        self.add_field(DialogFieldLabel(""))
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
                sgr = Common.generic_api_call(
                    "ec2",
                    "describe_security_groups",
                    {"GroupIds": self.secgroup_field.text},
                    "Describe Security Group",
                    "EC2",
                    subcategory="Security Group",
                    resource=self.secgroup_field.text,
                )
                if not sgr["Success"]:
                    return
                sg = sgr["Response"]

                snr = Common.generic_api_call(
                    "ec2",
                    "describe_subnets",
                    {"SubnetIds": self.subnet_field.text},
                    "Describe Subnet",
                    "EC2",
                    subcategory="Subnet",
                    resource=self.subnet_field.text,
                )
                if not snr["Success"]:
                    return
                sn = snr["Response"]

                if sg["VpcId"] == sn["VpcId"]:
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
