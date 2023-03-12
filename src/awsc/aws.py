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
        if "endpoint_url" in Common.Configuration["contexts"][Common.Session.context]:
            endpoint = Common.Configuration["contexts"][Common.Session.context][
                "endpoint_url"
            ]
        # print(f'Connecting to aws with keypair {access} / {secret} for context {Common.Session.context} on ')
        client = boto3.client(
            service,
            aws_access_key_id=access,
            aws_secret_access_key=secret,
            aws_session_token=session,
            config=config,
            endpoint_url=endpoint,
        )
        # return AWSSubprocessWrapper(client)
        return client

    # def assume_role(
    #     self,
    #     target_role,
    #     security_token="",
    #     mfa_device="",
    #     token="",
    #     session_name="awsc-session",
    #     duration=3600,
    #     keys=None,
    # ):
    #     if keys is None:
    #         if Common.Session.context not in Common.Configuration.keystore:
    #             access = None
    #             secret = None
    #         keys = Common.Configuration.keystore.force_resolve(Common.Session.context)
    #     access = keys["access"]
    #     secret = keys["secret"]
    #     endpoint = None
    #     if "endpoint_url" in Common.Configuration["contexts"][Common.Session.context]:
    #         endpoint = Common.Configuration["contexts"][Common.Session.context][
    #             "endpoint_url"
    #         ]
    #     if security_token == "" and mfa_device != "":
    #
    #         sts = boto3.client(
    #             "sts",
    #             aws_access_key_id=access,
    #             aws_secret_access_key=secret,
    #             config=self.conf(),
    #             endpoint=endpoint,
    #         )
    #         sts.get_session_t

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
