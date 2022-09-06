"""
Module for security group resources.
"""
from .base_control import Describer, MultiLister, ResourceLister
from .common import Common
from .resource_common import multilister_with_compare_path


class SGDescriber(Describer):
    """
    Describer control for security group resources.
    """

    prefix = "sg_browser"
    title = "Security Group"

    def __init__(self, *args, entry_key="group id", **kwargs):
        self.resource_key = "ec2"
        self.describe_method = "describe_security_groups"
        self.describe_kwarg_name = "GroupIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".SecurityGroups[0]"
        super().__init__(*args, entry_key=entry_key, **kwargs)


class SGRelated(MultiLister):
    """
    Lister control for AWS resources using a certain security group.
    """

    prefix = "sg_related"
    title = "Resources using Security Group"

    def title_info(self):
        return self.compare_value

    def __init__(self, *args, **kwargs):
        kwargs["compare_key"] = "group id"
        self.resource_descriptors = [
            multilister_with_compare_path("ec2", "[.SecurityGroups[].GroupId]", True),
            multilister_with_compare_path(
                "rds", "[.VpcSecurityGroups[].VpcSecurityGroupId]", True
            ),
        ]
        super().__init__(*args, **kwargs)


def _sg_determine_ingress_rules(self, result):
    return len(result["IpPermissions"])


def _sg_determine_egress_rules(self, result):
    return len(result["IpPermissionsEgress"])


class SGResourceLister(ResourceLister):
    """
    Lister control for security group resources.
    """

    prefix = "sg_list"
    title = "Security Groups"
    command_palette = ["sg", "securitygroup"]

    resource_type = "security group"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "Security Group"
    list_method = "describe_security_groups"
    item_path = ".SecurityGroups"
    columns = {
        "group id": {
            "path": ".GroupId",
            "size": 30,
            "weight": 0,
        },
        "name": {
            "path": ".GroupName",
            "size": 30,
            "weight": 1,
            "sort_weight": 0,
        },
        "vpc": {
            "path": ".VpcId",
            "size": 15,
            "weight": 2,
        },
        "ingress rules": {
            "path": _sg_determine_ingress_rules,
            "size": 15,
            "weight": 3,
        },
        "egress rules": {
            "path": _sg_determine_egress_rules,
            "size": 15,
            "weight": 4,
        },
    }
    describe_command = SGDescriber.opener
    open_command = SGRelated.opener
    open_selection_arg = "compare_value"
    primary_key = "group id"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @ResourceLister.Autohotkey("i", "View ingress rules", True)
    def ingress(self, *args):
        """
        Hotkey callback for viewing ingress rules.
        """
        if self.selection is not None:
            Common.Session.push_frame(SGRuleLister.opener(sg_entry=self.selection))

    @ResourceLister.Autohotkey("e", "View egress rules", True)
    def egress(self, *args):
        """
        Hotkey callback for viewing egress rules.
        """
        if self.selection is not None:
            Common.Session.push_frame(
                SGRuleLister.opener(sg_entry=self.selection, egress=True)
            )


_sg_well_known = {
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


def _sg_rule_determine_name(self, rule):
    if rule["IpProtocol"] == "-1":
        return "<all>"
    if rule["FromPort"] != rule["ToPort"]:
        return ""
    if rule["FromPort"] not in _sg_well_known:
        return ""
    return _sg_well_known[rule["FromPort"]]


def _sg_rule_determine_protocol(self, rule):
    if rule["IpProtocol"] == "-1" or rule["IpProtocol"] == -1:
        return "<all>"
    return rule["IpProtocol"]


def _sg_rule_determine_ips(self, rule):
    if "IpRanges" not in rule:
        return ""
    return ",".join(cidrs["CidrIp"] for cidrs in rule["IpRanges"])


def _sg_rule_determine_sgs(self, rule):
    if "UserIdGroupPairs" not in rule:
        return ""
    return ",".join(pair["GroupId"] for pair in rule["UserIdGroupPairs"])


def _sg_rule_determine_port_range(self, rule):
    if rule["IpProtocol"] == "-1":
        return "0-65535"
    if rule["FromPort"] != rule["ToPort"]:
        return f"{rule['FromPort']}-{rule['ToPort']}"
    return str(rule["FromPort"])


class SGRuleLister(ResourceLister):
    """
    Lister object for security group rules.
    """

    prefix = "sg_rule_list"
    title = "SG Rules"

    resource_type = "security group"
    main_provider = "ec2"
    category = "EC2"
    subcategory = "Security Group"
    list_method = "describe_security_groups"
    item_path = ".SecurityGroups"
    columns = {
        "protocol": {
            "path": _sg_rule_determine_protocol,
            "size": 10,
            "weight": 0,
        },
        "name": {
            "path": _sg_rule_determine_name,
            "size": 5,
            "weight": 1,
        },
        "ip addresses": {
            "path": _sg_rule_determine_ips,
            "size": 40,
            "weight": 2,
        },
        "security groups": {
            "path": _sg_rule_determine_sgs,
            "size": 50,
            "weight": 3,
        },
        "port range": {
            "path": _sg_rule_determine_port_range,
            "size": 20,
            "weight": 4,
            "sort_weight": 0,
        },
    }
    describe_command = SGDescriber.opener
    open_command = SGRelated.opener
    open_selection_arg = "compare_value"
    primary_key = "group id"

    def title_info(self):
        gress = "Egress" if self.egress else "Ingress"
        return f"{gress}: {self.sg_entry['group id']}"

    def __init__(
        self,
        *args,
        sg_entry=None,
        egress=False,
        **kwargs,
    ):
        if sg_entry is None:
            raise ValueError("sg_entry is required")
        self.sg_entry = sg_entry
        self.egress = egress
        self.list_kwargs = {"GroupIds": [self.sg_entry["group id"]]}
        gress = "Egress" if egress else ""
        self.item_path = f".SecurityGroups[0].IpPermissions{gress}"
        super().__init__(*args, **kwargs)
