"""
Module for working with the AWS API.
"""

import os
import boto3
from botocore import config as botoconf
from botocore import exceptions as botoerror

from .common import Common


class AWS:
    """
    Class which bridges the boto3 class model with the awsc configuration model.
    """

    region_overrides = {"route53domains": "us-east-1"}

    signature_version_overrides = {"s3": "s3v4"}

    def __init__(self):
        """
        Initializes an AWS object.
        """
        Common.Session.context_update_hooks.append(self.idcaller)
        self.idcaller()

    def conf(self, svc=""):
        """
        Generates a boto3 configuration object from the current awsc session.

        Returns
        -------
        botocore.config.Config
            The configuration object with the region and signature version set.
        """
        region = (
            Common.Session.region
            if svc not in self.region_overrides
            else self.region_overrides[svc]
        )
        signature_version = (
            "v4"
            if svc not in self.signature_version_overrides
            else self.signature_version_overrides[svc]
        )
        return botoconf.Config(
            region_name=region,
            signature_version=signature_version,
        )

    def env_session(self):
        """
        Fetches the boto3 session for the AWS credentials configured in the process environment.

        Returns
        -------
        boto3.session.Session
            The session object corresponding to the current process environment.
        """
        return boto3.Session()

    def set_env(self):
        """
        Pushes AWS creds to os env.
        """
        if Common.Session.context not in Common.Configuration.keystore:
            return
        keys = Common.Configuration.keystore[Common.Session.context]
        os.environ["AWS_ACCESS_KEY_ID"] = keys['access']
        os.environ["AWS_SECRET_ACCESS_KEY"] = keys['secret']
        if 'session' in keys:
            os.environ["AWS_SESSION_TOKEN"] = keys['session']
    
    def clear_env(self):
        try:
            del os.environ["AWS_ACCESS_KEY_ID"]
        except KeyError:
            pass
        try:
            del os.environ["AWS_SECRET_ACCESS_KEY"]
        except KeyError:
            pass
        try:
            del os.environ["AWS_SESSION_TOKEN"]
        except KeyError:
            pass
        

    def __call__(self, service, keys=None):
        """
        Shorthand for boto3.client().

        Parameters
        ----------
        service : str
            The service parameter for boto3.client()
        keys : dict
            A dict-like object with the "access" and "secret" keys set. If None, the currently
            active keypair in the configuration is used.

        Returns
        -------
        object
            A boto3 client instance for the service.
        """
        config = self.conf(service)
        if not Common.Session.context_is_valid:
            return boto3.client(service)  # Let magic sort it out
        if keys is None:
            if Common.Session.context not in Common.Configuration.keystore:
                return boto3.client(service)  # Let magic sort it out
            keys = Common.Configuration.keystore[Common.Session.context]
        access = keys["access"]
        secret = keys["secret"]
        endpoint = None
        session = None
        if "session" in keys:
            session = keys["session"]
        if "endpoint_url" in Common.Configuration.enumerated_contexts()[Common.Session.context]:
            endpoint = Common.Configuration.enumerated_contexts()[Common.Session.context][
                "endpoint_url"
            ]
        client = boto3.client(
            service,
            aws_access_key_id=access,
            aws_secret_access_key=secret,
            aws_session_token=session,
            config=config,
            endpoint_url=endpoint,
        )
        return client

    def whoami(self, keys=None):
        """
        Shorthand for the GetCallerIdentity STS API call.

        Parameters
        ----------
        keys : dict
            A dict-like object with the "access" and "secret" keys set. If None, the currently
            active keypair in the configuration is used.

        Returns
        -------
        object
            The API response for GetCallerIdentity.
        """
        try:
            return self("sts", keys).get_caller_identity()
        except botoerror.NoCredentialsError:
            return {
                "UserId": "<UNAUTHENTICATED>",
                "Account": "<UNAUTHENTICATED>",
                "Arn": "arn:aws::::<UNAUTHENTICATED>",
            }

    def list_regions(self):
        """
        Shorthand for enumerating the result of the DescribeRegions EC2 API call.

        Returns
        -------
        list
            A list of valid region names for EC2.
        """
        return [
            region["RegionName"]
            for region in self("ec2").describe_regions(AllRegions=True)["Regions"]
        ]

    def idcaller(self):
        """
        Sets the info display for the account and user ID of the currently selected keypair.

        AWSC must be fully initialized before calling.
        """
        try:
            whoami = self.whoami()
            try:
                del Common.Session.info_display.special_colors["Account"]
            except KeyError:
                pass
            try:
                del Common.Session.info_display.special_colors["UserId"]
            except KeyError:
                pass
            Common.Session.info_display["UserId"] = whoami["UserId"]
            Common.Session.info_display["Account"] = whoami["Account"]
        except (botoerror.ClientError, KeyError) as error:
            Common.Session.info_display.special_colors["UserId"] = Common.color("error")
            Common.Session.info_display.special_colors["Account"] = Common.color(
                "error"
            )
            Common.Session.info_display["UserId"] = "ERROR"
            Common.Session.info_display["Account"] = "ERROR"
            if isinstance(error, botoerror.ClientError):
                Common.clienterror(
                    error,
                    "Identify caller",
                    "Core",
                    subcategory="STS",
                )
            else:
                Common.error(
                    str(error),
                    "Identify caller",
                    "Core",
                    subcategory="STS",
                )
