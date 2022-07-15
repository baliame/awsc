from .base_control import Describer, MultiLister, ResourceLister
from .common import Common


class SGResourceLister(ResourceLister):
    prefix = "sg_list"
    title = "Security Groups"
    command_palette = ["sg", "securitygroup"]

    def __init__(self, *args, **kwargs):
        self.resource_key = "ec2"
        self.list_method = "describe_security_groups"
        self.item_path = ".SecurityGroups"
        self.column_paths = {
            "group id": ".GroupId",
            "name": ".GroupName",
            "vpc": ".VpcId",
            "ingress rules": self.determine_ingress_rules,
            "egress rules": self.determine_egress_rules,
        }
        self.imported_column_sizes = {
            "group id": 30,
            "name": 30,
            "vpc": 15,
            "ingress rules": 20,
            "egress rules": 20,
        }
        self.describe_command = SGDescriber.opener
        self.open_command = SGRelated.opener
        self.open_selection_arg = "compare_value"

        self.imported_column_order = [
            "group id",
            "name",
            "vpc",
            "ingress rules",
            "egress rules",
        ]
        self.sort_column = "name"
        self.primary_key = "group id"
        super().__init__(*args, **kwargs)
        self.add_hotkey("i", self.ingress, "View ingress rules")
        self.add_hotkey("e", self.egress, "View egress rules")

    def determine_ingress_rules(self, sg):
        return len(sg["IpPermissions"])

    def determine_egress_rules(self, sg):
        return len(sg["IpPermissionsEgress"])

    def ingress(self, *args):
        if self.selection is not None:
            Common.Session.push_frame(SGRuleLister.opener(sg_entry=self.selection))

    def egress(self, *args):
        if self.selection is not None:
            Common.Session.push_frame(
                SGRuleLister.opener(sg_entry=self.selection, egress=True)
            )


class SGRuleLister(ResourceLister):
    prefix = "sg_rule_list"
    title = "SG Rules"
    well_known = {
        20: "ftp",
        22: "ssh",
        23: "telnet",
        25: "smtp",
        80: "http",
        110: "pop3",
        220: "imap",
        443: "https",
        989: "ftps",
        1437: "dashboard-agent",
        1443: "mssql",
        3306: "mysql",
        3389: "rdp",
        5432: "pgsql",
        6379: "redis",
        8983: "solr",
        9200: "es",
    }

    def title_info(self):
        return "{0}: {1}".format(
            "Egress" if self.egress else "Ingress", self.sg_entry["group id"]
        )

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        sg_entry=None,
        egress=False,
        *args,
        **kwargs
    ):
        self.resource_key = "ec2"
        self.list_method = "describe_security_groups"
        if sg_entry is None:
            raise ValueError("sg_entry is required")
        self.sg_entry = sg_entry
        self.egress = egress
        self.list_kwargs = {"GroupIds": [self.sg_entry["group id"]]}
        self.item_path = ".SecurityGroups[0].IpPermissions{0}".format(
            "Egress" if egress else ""
        )
        self.column_paths = {
            "protocol": self.determine_protocol,
            "name": self.determine_name,
            "ip addresses": self.determine_ips,
            "security groups": self.determine_sgs,
            "port range": self.determine_port_range,
        }
        self.imported_column_sizes = {
            "name": 10,
            "protocol": 5,
            "ip addresses": 40,
            "security groups": 50,
            "port range": 20,
        }
        self.imported_column_order = [
            "name",
            "protocol",
            "ip addresses",
            "security groups",
            "port range",
        ]
        self.sort_column = "port range"
        super().__init__(parent, alignment, dimensions, *args, **kwargs)

    def determine_name(self, rule):
        if rule["IpProtocol"] == "-1":
            return "<all>"
        if rule["FromPort"] != rule["ToPort"]:
            return ""
        if rule["FromPort"] not in SGRuleLister.well_known:
            return ""
        return SGRuleLister.well_known[rule["FromPort"]]

    def determine_protocol(self, rule):
        if rule["IpProtocol"] == "-1" or rule["IpProtocol"] == -1:
            return "<all>"
        return rule["IpProtocol"]

    def determine_ips(self, rule):
        if "IpRanges" not in rule:
            return ""
        return ",".join(cidrs["CidrIp"] for cidrs in rule["IpRanges"])

    def determine_sgs(self, rule):
        if "UserIdGroupPairs" not in rule:
            return ""
        return ",".join(pair["GroupId"] for pair in rule["UserIdGroupPairs"])

    def determine_port_range(self, rule):
        if rule["IpProtocol"] == "-1":
            return "0-65535"
        if rule["FromPort"] != rule["ToPort"]:
            return "{0}-{1}".format(rule["FromPort"], rule["ToPort"])
        return str(rule["FromPort"])


class SGDescriber(Describer):
    prefix = "sg_browser"
    title = "Security Group"

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        entry,
        *args,
        entry_key="group id",
        **kwargs
    ):
        self.resource_key = "ec2"
        self.describe_method = "describe_security_groups"
        self.describe_kwarg_name = "GroupIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".SecurityGroups[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class SGRelated(MultiLister):
    prefix = "sg_related"
    title = "Resources using Security Group"

    def title_info(self):
        return self.compare_value

    def __init__(self, *args, **kwargs):
        kwargs["compare_key"] = "group id"
        self.resource_descriptors = [
            {
                "resource_key": "ec2",
                "list_method": "describe_instances",
                "list_kwargs": {},
                "item_path": "[.Reservations[].Instances[]]",
                "column_paths": {
                    "type": lambda x: "EC2 Instance",
                    "id": ".InstanceId",
                    "name": self.tag_finder_generator("Name"),
                },
                "hidden_columns": {},
                "compare_as_list": True,
                "compare_path": "[.SecurityGroups[].GroupId]",
            },
            {
                "resource_key": "rds",
                "list_method": "describe_db_instances",
                "list_kwargs": {},
                "item_path": ".DBInstances",
                "column_paths": {
                    "type": lambda x: "RDS Instance",
                    "id": ".DBInstanceIdentifier",
                    "name": ".Endpoint.Address",
                },
                "hidden_columns": {},
                "compare_as_list": True,
                "compare_path": "[.VpcSecurityGroups[].VpcSecurityGroupId]",
            },
        ]
        super().__init__(*args, **kwargs)
