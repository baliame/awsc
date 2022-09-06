"""
Module for working with the AWS API.
"""

import boto3
from botocore import config as botoconf
from botocore import exceptions as botoerror

from .common import Common


class AWS:
    """
    Class which bridges the boto3 class model with the awsc configuration model.
    """

    def __init__(self):
        """
        Initializes an AWS object.
        """
        Common.Session.context_update_hooks.append(self.idcaller)
        self.idcaller()

    def conf(self):
        """
        Generates a boto3 configuration object from the current awsc session.

        Returns
        -------
        botocore.config.Config
            The configuration object with the region and signature version set.
        """
        return botoconf.Config(
            region_name=Common.Session.region,
            signature_version="v4",
        )

    def s3conf(self):
        """
        Generates a boto3 configuration object for s3 from the current awsc session.

        Returns
        -------
        botocore.config.Config
            The configuration object with the region and signature version set.
        """
        return botoconf.Config(
            region_name=Common.Session.region,
            signature_version="s3v4",
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
        if service == "s3":
            config = self.s3conf()
        else:
            config = self.conf()
        client = boto3.client(
            service,
            aws_access_key_id=keys["access"]
            if keys is not None
            else Common.Configuration.keystore[Common.Session.context]["access"],
            aws_secret_access_key=keys["secret"]
            if keys is not None
            else Common.Configuration.keystore[Common.Session.context]["secret"],
            config=config,
        )
        # return AWSSubprocessWrapper(client)
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
        return self("sts", keys).get_caller_identity()

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
