"""
Module for EKS clusters.
"""
import subprocess
from pathlib import Path

import yaml

from .arn import ARN
from .base_control import Describer, ResourceLister
from .common import Common


class EKSDescriber(Describer):
    """
    Describer control for EKS clusters.
    """

    prefix = "eks_browser"
    title = "EKS Cluster"

    resource_type = "eks cluster"
    main_provider = "eks"
    category = "EKS"
    subcategory = "Clusters"
    describe_method = "describe_cluster"
    describe_kwarg_name = "name"
    object_path = ".cluster"


class EKSResourceLister(ResourceLister):
    """
    Lister control for EKS clusters.
    """

    prefix = "eks_list"
    title = "EKS Clusters"
    command_palette = ["eks", "kubernetes"]

    resource_type = "eks cluster"
    main_provider = "eks"
    category = "EKS"
    subcategory = "Clusters"
    list_method = "list_clusters"
    item_path = ".clusters"
    columns = {
        "name": {
            "path": ".",
            "size": 100,
            "weight": 1,
            "sort_weight": 1,
        }
    }
    describe_command = EKSDescriber.opener

    @ResourceLister.Autohotkey("k", "Fetch kube context", True)
    def fetch_kubecontext(self, _):
        kc_path = Path.home() / ".kube" / "config"
        if kc_path.exists():
            with kc_path.open("r") as file:
                kubeconfig = yaml.safe_load(file.read())
        else:
            kubeconfig = {
                "apiVersion": "v1",
                "kind": "Config",
                "clusters": [],
                "contexts": [],
                "users": [],
                "preferences": {},
            }
        resp = Common.generic_api_call(
            "eks",
            "describe_cluster",
            {"name": self.selection["name"]},
            "Describe EKS cluster",
            "EKS",
            subcategory="Cluster",
            resource=self.selection["name"],
        )
        if resp["Success"]:
            cluster_data = resp["Response"]
            endpoint = cluster_data["cluster"]["endpoint"]
            ca_data = cluster_data["cluster"]["certificateAuthority"]["data"]
            cluster_arn = cluster_data["cluster"]["arn"]
            cluster_arn_parsed = ARN(cluster_arn)

            idx = -1
            for cidx, elem in enumerate(kubeconfig["clusters"]):
                if elem["name"] == cluster_arn:
                    idx = cidx
                    break
            cluster = {"certificate-authority-data": ca_data, "server": endpoint}
            if idx == -1:
                obj = {"cluster": cluster, "name": cluster_arn}
                kubeconfig["clusters"].append(obj)
            else:
                kubeconfig["clusters"][idx]["cluster"] = cluster

            idx = -1
            for cidx, elem in enumerate(kubeconfig["contexts"]):
                if elem["name"] == cluster_arn:
                    idx = cidx
                    break
            context = {"cluster": cluster_arn, "user": cluster_arn}
            if idx == -1:
                obj = {"context": context, "name": cluster_arn}
                kubeconfig["contexts"].append(obj)
            else:
                kubeconfig["contexts"][idx]["context"] = context

            idx = -1
            for cidx, elem in enumerate(kubeconfig["users"]):
                if elem["name"] == cluster_arn:
                    idx = cidx
                    break
            user = {
                "exec": {
                    "apiVersion": "client.authentication.k8s.io/v1beta1",
                    "command": "aws",
                    "args": [
                        "--region",
                        cluster_arn_parsed.region,
                        "eks",
                        "get-token",
                        "--cluster-name",
                        cluster_arn_parsed.resource_id_first,
                        "--profile",
                        Common.Session.context,
                    ],
                }
            }
            if idx == -1:
                obj = {"user": user, "name": cluster_arn}
                kubeconfig["users"].append(obj)
            else:
                kubeconfig["users"][idx]["user"] = user

            kubeconfig["current-context"] = cluster_arn

            with kc_path.open("w", encoding="utf-8") as file:
                file.write(yaml.dump(kubeconfig))

            Common.Session.set_message(
                f"Successfully wrote configuration {cluster_arn} to ~/.kube/config.",
                Common.color("message_success"),
            )
            return True
        return False

    @ResourceLister.Autohotkey("9", "k9s", True)
    def open_k9s(self, _):
        if self.fetch_kubecontext(_):
            exit_code = Common.Session.ui.unraw(
                subprocess.run,
                [
                    "k9s",
                ],
            )
            Common.Session.set_message(
                f"k9s exited with code {exit_code.returncode}",
                Common.color("message_info"),
            )
