"""
Module for route 53 resources.
"""
import datetime
import json

from .base_control import (
    Describer,
    ListResourceDocumentCreator,
    ListResourceFieldsEditor,
    ResourceLister,
    SelectionAttribute,
    SelectionControllerDataAttribute,
    TemplateDict,
)
from .common import Common
from .termui.ui import ControlCodes


class R53RecordDescriber(Describer):
    """
    Describer control for Route 53 record sets.
    """

    prefix = "r53_record_browser"
    title = "Route53 Record"

    def populate_entry(self, *args, entry, **kwargs):
        super().populate_entry(*args, entry=entry, **kwargs)
        self.record_type = entry["entry"]
        self.record_name = entry["name"]

    def populate_describe_kwargs(self, *args, **kwargs):
        super().populate_describe_kwargs(*args, **kwargs)
        self.describe_kwargs["StartRecordType"] = self.record_type
        self.describe_kwargs["StartRecordName"] = self.record_name

    def __init__(self, *args, entry_key="hosted_zone_id", **kwargs):
        self.resource_key = "route53"
        self.describe_method = "list_resource_record_sets"
        self.describe_kwarg_name = "HostedZoneId"
        self.object_path = ".ResourceRecordSets[0]"
        super().__init__(*args, entry_key=entry_key, **kwargs)

    def title_info(self):
        return f"{self.record_type} {self.record_name}"


def _r53_record_is_alias(result):
    return "AliasTarget" in result and result["AliasTarget"]["DNSName"] != ""


def _r53_record_determine_records(result):
    if _r53_record_is_alias(result):
        return result["AliasTarget"]["DNSName"]
    return ",".join([record["Value"] for record in result["ResourceRecords"]])


def _r53_record_determine_name(result):
    """
    Column callback for the name of a route 53 record.
    """
    return result["Name"].replace("\\052", "*")


class R53RecordLister(ResourceLister):
    """
    Lister control for route 53 recordsets.
    """

    prefix = "r53_record_list"
    title = "Route53 Recordsets"

    resource_type = "recordset"
    main_provider = "route53"
    category = "Route 53"
    subcategory = "Recordsets"
    list_method = "list_resource_record_sets"
    item_path = ".ResourceRecordSets"
    columns = {
        "entry": {
            "path": ".Type",
            "size": 5,
            "weight": 0,
            "sort_weight": 0,
        },
        "name": {
            "path": _r53_record_determine_name,
            "size": 30,
            "weight": 1,
            "sort_weight": 1,
        },
        "records": {
            "path": _r53_record_determine_records,
            "size": 60,
            "weight": 2,
        },
        "ttl": {
            "path": ".TTL",
            "size": 5,
            "weight": 3,
        },
    }
    primary_key = "name"
    describe_command = R53RecordDescriber.opener

    def title_info(self):
        return self.r53_entry["name"]

    def __init__(self, *args, r53_entry, **kwargs):
        self.r53_entry = r53_entry
        self.list_kwargs = {"HostedZoneId": self.r53_entry["id"]}
        super().__init__(*args, **kwargs)

    @ResourceLister.Autohotkey(ControlCodes.D, "Delete record", True)
    def delete_record(self, _):
        """
        Hotkey callback for deleting a record.
        """
        self.confirm_template(
            "change_resource_record_sets",
            TemplateDict(
                {
                    "HostedZoneId": self.r53_entry["id"],
                    "ChangeBatch": {
                        "Changes": [
                            {
                                "Action": "DELETE",
                                "ResourceRecordSet": {
                                    "Name": SelectionAttribute("name"),
                                    "Type": SelectionAttribute("entry"),
                                    "ResourceRecords": SelectionControllerDataAttribute(
                                        "ResourceRecords"
                                    ),
                                },
                            }
                        ]
                    },
                }
            ),
        )(self.selection)

    @ResourceLister.Autohotkey("n", "Add new record")
    def create(self, _):
        """
        Hotkey callback for adding a new record.
        """
        R53RecordCreator(self.r53_entry["id"]).edit()
        self.refresh_data()

    # TODO: Use new editor class if possible
    @ResourceLister.Autohotkey("e", "Edit", True)
    def edit(self, _):
        """
        Hotkey callback for editing an existing record set.
        """
        if self.selection is not None:
            raw = self.selection.controller_data
            if not _r53_record_is_alias(raw):
                content = "\n".join(
                    record["Value"] for record in raw["ResourceRecords"]
                )
                newcontent = Common.Session.textedit(content).strip(" \n\t")
                if content == newcontent:
                    Common.Session.set_message(
                        "Input unchanged.", Common.color("message_info")
                    )
                    return
                newcontent = newcontent.split("\n")
                Common.generic_api_call(
                    "route53",
                    "change_resource_record_sets",
                    {
                        "HostedZoneId": self.selection["hosted_zone_id"],
                        "ChangeBatch": {
                            "Changes": [
                                {
                                    "Action": "UPSERT",
                                    "ResourceRecordSet": {
                                        "Name": self.selection["name"],
                                        "Type": self.selection["entry"],
                                        "ResourceRecords": [
                                            {"Value": line} for line in newcontent
                                        ],
                                        "TTL": int(self.selection["ttl"]),
                                    },
                                }
                            ]
                        },
                    },
                    "Edit DNS record",
                    "Route53",
                    subcategory="Hosted Zone",
                    success_template="Modified DNS entry for zone {0}",
                    resource=self.selection["hosted_zone_id"],
                )

                self.refresh_data()
            else:
                Common.Session.set_message(
                    "Cannot edit aliased records", Common.color("message_info")
                )


class R53Describer(Describer):
    """
    Describer control for route 53 hosted zones.
    """

    prefix = "r53_browser"
    title = "Route53 Hosted Zone"

    def __init__(self, *args, entry_key="id", **kwargs):
        self.resource_key = "route53"
        self.describe_method = "get_hosted_zone"
        self.describe_kwarg_name = "Id"
        self.object_path = "."
        super().__init__(*args, entry_key=entry_key, **kwargs)


class R53ResourceLister(ResourceLister):
    """
    Lister control for route 53 hosted zones.
    """

    prefix = "r53_list"
    title = "Route53 Hosted Zones"
    command_palette = ["r53", "route53"]

    resource_type = "hosted zone"
    main_provider = "route53"
    category = "Route 53"
    subcategory = "Hosted Zones"
    list_method = "list_hosted_zones"
    item_path = ".HostedZones"
    columns = {
        "id": {
            "path": ".Id",
            "size": 30,
            "weight": 0,
            "sort_weight": 1,
        },
        "name": {
            "path": ".Name",
            "size": 30,
            "weight": 1,
            "sort_weight": 0,
        },
        "records": {
            "path": ".ResourceRecordSetCount",
            "size": 7,
            "weight": 2,
        },
    }
    primary_key = "id"
    describe_command = R53Describer.opener
    open_command = R53RecordLister.opener
    open_selection_arg = "r53_entry"

    @ResourceLister.Autohotkey(ControlCodes.D, "Delete hosted zone", True)
    def delete_hosted_zone(self, _):
        """
        Hotkey callback for deleting a hosted zone.
        """
        self.confirm_template(
            "delete_hosted_Zone",
            TemplateDict(
                {
                    "Id": SelectionAttribute("id"),
                }
            ),
        )(self.selection)

    @ResourceLister.Autohotkey("n", "Create hosted zone")
    def create(self, _):
        """
        Hotkey callback for creating a new hosted zone.
        """
        ListResourceDocumentCreator(
            "route53",
            "created_hosted_zone",
            None,
            initial_document={
                "Name": "",
                "VPC": {
                    "VPCRegion": "",
                    "VPCId": "",
                },
                "CallerReference": datetime.datetime.now().isoformat(),
                "HostedZoneConfig": {
                    "Comment": "",
                    "PrivateZone": False,
                },
                "DelegationSetId": "",
            },
        ).edit()


class R53RecordCreator(ListResourceDocumentCreator):
    """
    Custom creator class for creating Route 53 record sets. Route 53 has a strongly non-standard API.
    """

    def __init__(self, hosted_zone_id, *args, **kwargs):
        self.hosted_zone_id = hosted_zone_id
        super().__init__(
            "route53",
            "change_resource_record_sets",
            None,
            initial_document={
                "Name": "",
                "Type": "A",
                "ResourceRecords": [
                    {
                        "Value": "",
                    }
                ],
                "TTL": 30,
            },
        )

    def generate_kwargs(self, selection, newcontent):
        update_data = json.loads(newcontent)
        return {
            "HostedZoneId": self.hosted_zone_id,
            "ChangeBatch": {
                "Changes": [{"Action": "CREATE", "ResourceRecordSet": update_data}],
            },
        }


def _r53_healthcheck_determine_uri(result):
    """
    Column callback for fetching the URI for a route 53 healtcheck.
    """
    hcc = result["HealthCheckConfig"]
    if hcc["Type"] == "CLOUDWATCH_METRIC":
        cwac = result["CloudwatchAlarmConfiguration"]
        if cwac["ComparisonOperator"] == "GreaterThanOrEqualToThreshold":
            op = ">="
        elif cwac["ComparisonOperator"] == "GreaterThanThreshold":
            op = ">"
        elif cwac["ComparisonOperator"] == "LessThanOrEqualToThreshold":
            op = "<="
        elif cwac["ComparisonOperator"] == "LessThanThreshold":
            op = "<"
        else:
            op = "?"
        return f"<cloudwatch>: {cwac['MetricName']} {op} {cwac['Threshold']}"
    if hcc["Type"] == "CALCULATED":
        return "<calculated>"
    if hcc["Type"] == "RECOVERY_CONTROL":
        return "<recovery control>"
    if ["IPAddress"] in hcc and hcc["IPAddress"] != "":
        host = hcc["IPAddress"]
    else:
        host = hcc["FullyQualifiedDomainName"]
    if hcc["Type"] in ["HTTP", "HTTP_STR_MATCH"]:
        protocol = "http"
    elif hcc["Type"] in ["HTTPS", "HTTPS_STR_MATCH"]:
        protocol = "https"
    elif hcc["Type"] == "TCP":
        protocol = "tcp"
    else:
        protocol = f"unknown({hcc['Type']})"
    return f"{protocol}://{host}:{hcc['Port']}{hcc['ResourcePath']}"


def _r53_healthcheck_determine_status(result):
    """
    Column callback for determining a healthcheck status.
    """
    resp = Common.generic_api_call(
        "route53",
        "get_health_check_status",
        {"HealthCheckId": result["Id"]},
        "Get Health Check Status",
        "Route53",
        subcategory="Health Check",
        resource=result["Id"],
    )
    if resp["Success"]:
        return resp["Response"]["HealthCheckObservations"]["StatusReport"]["Status"]
    return "<n/a>"


class R53HealthCheckLister(ResourceLister):
    """
    Lister control for Route 53 health checks.
    """

    prefix = "r53_health_check_list"
    title = "Route53 Health Checks"
    # NOTE: healthcheck may conflict with other services
    # if it does, remove and only allow more explicit commands
    command_palette = ["r53healthcheck", "route53healthcheck", "healthcheck"]

    @ResourceLister.Autohotkey("n", "Create health check")
    def create_health_check(self, _):
        """
        Hotkey callback for creating a new health check.
        """
        ListResourceDocumentCreator(
            "route53",
            "create_health_check",
            "HealthCheckConfig",
            initial_document={
                "IPAddress": "string",
                "Port": 80,
                "Type": "HTTP",
                "ResourcePath": "/",
                "FullyQualifiedDomainName": "string",
                "SearchString": "string",
                "RequestInterval": 30,
                "FailureThreshold": 3,
                "MeasureLatency": False,
                "Inverted": False,
                "Disabled": False,
                "HealthThreshold": 0,
                "ChildHealthChecks": [
                    "string",
                ],
                "EnableSNI": True,
                "Regions": [
                    "us-east-1",
                ],
                "AlarmIdentifier": {"Region": "us-east-1", "Name": "string"},
                "InsufficientDataHealthStatus": "Unhealthy",
                "RoutingControlArn": "string",
            },
            as_json=True,
            static_fields={},
            message="Create successful",
        ).edit()

    @ResourceLister.Autohotkey("e", "Edit health check", True)
    def edit_health_check(self, _):
        """
        Hotkey callback for editing a health check.
        """
        ListResourceFieldsEditor(
            "route53",
            "get_health_check",
            ".HealthCheck.HealthCheckConfig",
            "update_health_check",
            "HealthCheckId",
            {
                "IPAddress": ".IPAddress",
                "Port": ".Port",
                "ResourcePath": ".ResourcePath",
                "FullyQualifiedDomainName": ".FullyQualifiedDomainName",
                "SearchString": ".SearchString",
                "FailureThreshold": ".FailureThreshold",
                "Inverted": ".Inverted",
                "Disabled": ".Disabled",
                "HealthThreshold": ".HealthThreshold",
                "ChildHealthChecks": ".ChildHealthChecks",
                "EnableSNI": ".EnableSNI",
                "Regions": ".Regions",
                "AlarmIdentifier": ".AlarmIdentifier",
                "InsufficientDataHealthStatus": ".InsufficientDataHealthStatus",
                "ResetElements": "[]",
            },
            entry_key="id",
            as_json=[
                "ChildHealthChecks",
                "Regions",
                "AlarmIdentifier",
                "ResetElements",
            ],
        ).edit(self.selection)

    @ResourceLister.Autohotkey(ControlCodes.D, "Delete health check", True)
    def delete_health_check(self, _):
        """
        Hotkey callback for deleting a health check.
        """
        self.confirm_template(
            "delete_health_check",
            TemplateDict(
                {
                    "HealthCheckId": SelectionAttribute("id"),
                }
            ),
        )(self.selection)

    resource_type = "route53 health check"
    main_provider = "route53"
    category = "Route 53"
    subcategory = "Health Check"
    list_method = "list_health_checks"
    item_path = ".HealthChecks"
    columns = {
        "id": {
            "path": ".Id",
            "size": 30,
            "weight": 0,
            "sort_weight": 1,
        },
        "uri": {
            "path": _r53_healthcheck_determine_uri,
            "size": 90,
            "weight": 1,
            "sort_weight": 1,
        },
        "inverted": {
            "path": ".HealthCheckConfig.Inverted",
            "size": 10,
            "weight": 2,
        },
        "disabled": {
            "path": ".HealthCheckConfig.Disabled",
            "size": 10,
            "weight": 3,
        },
        "status": {
            "path": _r53_healthcheck_determine_status,
            "size": 15,
            "weight": 4,
        },
        "name": {
            "path": ".Id",
            "size": 30,
            "hidden": True,
        },
    }
    primary_key = "id"
    # describe_command = R53HealthCheckDescriber.opener
