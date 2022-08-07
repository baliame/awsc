import datetime
import json

from .base_control import (
    DeleteResourceDialog,
    Describer,
    ListResourceDocumentCreator,
    ListResourceFieldsEditor,
    ResourceLister,
)
from .common import Common
from .termui.alignment import CenterAnchor, Dimension
from .termui.ui import ControlCodes


class R53ResourceLister(ResourceLister):
    prefix = "r53_list"
    title = "Route53 Hosted Zones"
    command_palette = ["r53", "route53"]

    def delete_hosted_zone(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="route53 hosted zone",
            resource_identifier=self.selection["id"],
            callback=self.do_delete,
            action_name="Delete",
            can_force=True,
        )

    def do_delete(self, **kwargs):
        if self.selection is None:
            return
        api_kwargs = {
            "Id": self.selection["id"],
        }
        Common.generic_api_call(
            "route53",
            "delete_hosted_zone",
            api_kwargs,
            "Delete hosted zone",
            "Route53",
            subcategory="Hosted Zone",
            success_template="Deleting hosted zone {0}",
            resource=self.selection["id"],
        )
        self.refresh_data()

    def create(self, _):
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

    def __init__(self, *args, **kwargs):
        self.resource_key = "route53"
        self.list_method = "list_hosted_zones"
        self.item_path = ".HostedZones"
        self.column_paths = {
            "id": ".Id",
            "name": ".Name",
            "records": ".ResourceRecordSetCount",
        }
        self.imported_column_sizes = {
            "id": 30,
            "name": 30,
            "records": 5,
        }
        self.describe_command = R53Describer.opener
        self.open_command = R53RecordLister.opener
        self.open_selection_arg = "r53_entry"
        self.primary_key = "id"

        self.imported_column_order = ["id", "name", "records"]
        self.sort_column = "name"
        super().__init__(*args, **kwargs)
        self.add_hotkey(ControlCodes.D, self.delete_hosted_zone, "Delete hosted zone")
        self.add_hotkey("n", self.create, "Create hosted zone")


class R53RecordCreator(ListResourceDocumentCreator):
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


class R53RecordLister(ResourceLister):
    prefix = "r53_record_list"
    title = "Route53 Records"

    def title_info(self):
        return self.r53_entry["name"]

    def __init__(self, *args, r53_entry, **kwargs):
        self.r53_entry = r53_entry
        self.resource_key = "route53"
        self.list_method = "list_resource_record_sets"
        self.list_kwargs = {"HostedZoneId": self.r53_entry["id"]}
        self.item_path = ".ResourceRecordSets"
        self.column_paths = {
            "entry": ".Type",
            "name": self.determine_name,
            "records": self.determine_records,
            "ttl": ".TTL",
        }
        self.hidden_columns = {
            "hosted_zone_id": self.determine_hosted_zone_id,
        }
        self.imported_column_sizes = {
            "entry": 5,
            "name": 30,
            "records": 60,
            "ttl": 5,
        }
        self.describe_command = R53RecordDescriber.opener

        self.imported_column_order = ["entry", "name", "records", "ttl"]
        self.sort_column = "name"
        self.primary_key = None
        super().__init__(*args, **kwargs)
        self.add_hotkey("e", self.edit, "Edit")
        self.add_hotkey("n", self.create, "Add new record")
        self.add_hotkey(ControlCodes.D, self.delete_record, "Delete record")

    def determine_hosted_zone_id(self, _):
        return self.r53_entry["id"]

    def determine_name(self, result):
        return result["Name"].replace("\\052", "*")

    def delete_record(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="route53 DNS entry",
            resource_identifier=f"{self.selection['entry']} {self.selection['name']}",
            callback=self.do_delete,
            action_name="Delete",
            can_force=True,
        )

    def do_delete(self, **kwargs):
        if self.selection is None:
            return
        Common.generic_api_call(
            "route53",
            "change_resource_record_sets",
            {
                "HostedZoneId": self.selection["hosted_zone_id"],
                "ChangeBatch": {
                    "Changes": [
                        {
                            "Action": "DELETE",
                            "ResourceRecordSet": {
                                "Name": self.selection["name"],
                                "Type": self.selection["entry"],
                                "ResourceRecords": self.selection.controller_data[
                                    "ResourceRecords"
                                ],
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

    def create(self, _):
        R53RecordCreator(self.r53_entry["id"]).edit()
        self.refresh_data()

    # TODO: Use new editor class if possible
    def edit(self, _):
        if self.selection is not None:
            raw = self.selection.controller_data
            if not self.is_alias(raw):
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

    def is_alias(self, result):
        return "AliasTarget" in result and result["AliasTarget"]["DNSName"] != ""

    def determine_records(self, result):
        if self.is_alias(result):
            return result["AliasTarget"]["DNSName"]
        return ",".join([record["Value"] for record in result["ResourceRecords"]])


class R53Describer(Describer):
    prefix = "r53_browser"
    title = "Route53 Hosted Zone"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="id", **kwargs
    ):
        self.resource_key = "route53"
        self.describe_method = "get_hosted_zone"
        self.describe_kwarg_name = "Id"
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


class R53RecordDescriber(Describer):
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

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        entry,
        *args,
        entry_key="hosted_zone_id",
        **kwargs,
    ):
        self.resource_key = "route53"
        self.describe_method = "list_resource_record_sets"
        self.describe_kwarg_name = "HostedZoneId"
        self.object_path = ".ResourceRecordSets[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs,
        )

    def title_info(self):
        return f"{self.record_type} {self.record_name}"


class R53HealthCheckLister(ResourceLister):
    prefix = "r53_health_check_list"
    title = "Route53 Health Checks"
    # TODO: healthcheck may conflict with other services
    # if it does, remove and only allow more explicit commands
    command_palette = ["r53healthcheck", "route53healthcheck", "healthcheck"]

    def create_health_check(self, _):
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

    def edit_health_check(self, _):
        if self.selection is None:
            return
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

    def delete_health_check(self, _):
        if self.selection is None:
            return
        DeleteResourceDialog(
            self.parent,
            CenterAnchor(0, 0),
            Dimension("80%|40", "10"),
            caller=self,
            resource_type="route53 health check",
            resource_identifier=self.selection["id"],
            callback=self.do_delete,
            action_name="Delete",
            can_force=True,
        )

    def do_delete(self, **kwargs):
        if self.selection is None:
            return
        api_kwargs = {
            "HealthCheckId": self.selection["id"],
        }
        Common.generic_api_call(
            "route53",
            "delete_health_check",
            api_kwargs,
            "Delete health check",
            "Route53",
            subcategory="Health check",
            success_template="Deleting health check {0}",
            resource=self.selection["id"],
        )
        self.refresh_data()

    def __init__(self, *args, **kwargs):
        self.resource_key = "route53"
        self.list_method = "list_health_checks"
        self.item_path = ".HealthChecks"
        self.column_paths = {
            "id": ".Id",
            "uri": self.determine_healthcheck_uri,
            "inverted": ".HealthCheckConfig.Inverted",
            "disabled": ".HealthCheckConfig.Disabled",
            "status": self.determine_healthcheck_status,
        }
        self.imported_column_sizes = {
            "id": 30,
            "records": 5,
        }
        self.hidden_columns = {"name": ".Id"}
        self.describe_command = R53Describer.opener
        self.open_command = R53RecordLister.opener
        self.open_selection_arg = "r53_entry"
        self.primary_key = "id"

        self.imported_column_order = ["id", "name", "records"]
        self.sort_column = "name"
        super().__init__(*args, **kwargs)

    def determine_healthcheck_uri(self, result):
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

        elif hcc["Type"] == "CALCULATED":
            return "<calculated>"
        elif hcc["Type"] == "RECOVERY_CONTROL":
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

    def determine_healthcheck_status(self, result):
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
        else:
            return "<n/a>"
