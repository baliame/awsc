from multiprocessing import Pipe, Process

import boto3
from botocore import config as botoconf
from botocore import exceptions as botoerror

from .common import Common


class AWSSubprocessWrapper:
    def __init__(self, client):
        self.client = client

    def __getattr__(self, attr):
        if hasattr(self.client, attr):
            attribute = getattr(self.client, attr)
            if callable(attribute):
                return AWSSubprocessWrapper.SubprocessCallWrapper(attribute)
            return attribute
        raise AttributeError

    class SubprocessCallWrapper:
        def __init__(self, target):
            self.target = target

        def __call__(self, *args, **kwargs):
            own, remote = Pipe(False)
            process = Process(
                target=self.execute, args=[remote, *args], kwargs=kwargs, daemon=True
            )
            process.start()
            process.join()
            data = own.recv()
            if isinstance(data, Exception):
                raise data
            return data

        def execute(self, remote, *args, **kwargs):
            try:
                data = self.target(*args, **kwargs)
            # pylint: disable=broad-except # It's an arbitrary function call.
            except Exception as error:
                remote.send(error)
            remote.send(data)


class AWS:
    def __init__(self):
        Common.Session.context_update_hooks.append(self.idcaller)
        self.idcaller()

    def conf(self):
        return botoconf.Config(
            region_name=Common.Session.region,
            signature_version="v4",
        )

    def s3conf(self):
        return botoconf.Config(
            region_name=Common.Session.region,
            signature_version="s3v4",
        )

    def env_session(self):
        return boto3.Session()

    def __call__(self, service, keys=None):
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
        return self("sts", keys).get_caller_identity()

    def list_regions(self):
        return [
            region["RegionName"]
            for region in self("ec2").describe_regions(AllRegions=True)["Regions"]
        ]

    def idcaller(self):
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
