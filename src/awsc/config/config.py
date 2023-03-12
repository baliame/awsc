"""
Module for the configuration parser object.
"""
import sys
from pathlib import Path

import yaml

from .scheme import Scheme
from .storage import Keystore

LAST_CONFIG_VERSION = 19


class Config:
    """
    Configuration parser and holder.

    Attributes
    ----------
    version_updaters : dict
        A numbered dict of update functions for incrementally upgrading an outdated configuration file.
    path : pathlib.Path
        The configuration parent path, where all configuration data is stored.
    config_path : pathlib.Path
        The path to the configuration yaml file.
    keystore : awsc.config.storage.Keystore
        The key storage holder instance.
    scheme : awsc.config.scheme.Scheme
        The color scheme holder instance.
    config : dict
        The loaded configuration.
    """

    def __init__(self, path=None):
        """
        Initializes a Config object.

        Parameters
        ----------
        path : str
            The configuration parent path, if not default. Defaults to ~/.config/awsc.
        """
        print("Initializing AWSC configuration...", file=sys.stderr)
        self.version_updaters = {
            1: self._update_1,
            2: self._update_2,
            3: self._update_3,
            4: self._update_4,
            5: self._update_5,
            6: self._update_6,
            7: self._update_7,
            8: self._update_8,
            9: self._update_9,
            10: self._update_10,
            11: self._update_11,
            12: self._update_12,
            13: self._update_13,
            14: self._update_14,
            15: self._update_15,
            16: self._update_16,
            17: self._update_17,
            18: self._update_18,
            19: self._update_19,
        }
        if path is None:
            path = Path.home() / ".config" / "awsc"
        else:
            path = Path(path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.keystore = Keystore(self)
        self.scheme = Scheme(self)

        self.config_path = self.path / "config.yaml"

        if not self.config_path.exists():
            self.create_default_config()
        else:
            self.parse_config()

    def initialize(self):
        """
        Late initializer for the Config object. Should be called after everything has been instantiated
        but before anything is being used.
        """
        self.keystore.unlock()
        self.update_version()

    def _update_1(self):
        """
        Version 1 configuration update.

        Do not call.
        """
        self.config["default_region"] = "us-east-1"

    def _update_2(self):
        """
        Version 2 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()

    def _update_3(self):
        """
        Version 3 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()

    def _update_4(self):
        """
        Version 4 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()
        self.config["usage_statistics"] = {
            "regions_by_context": {},
            "resources_by_context": {},
        }

    def _update_5(self):
        """
        Version 5 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()

    def _update_6(self):
        """
        Version 6 configuration update.

        Do not call.
        """
        self.config["default_ssh_key"] = "id_rsa"

    def _update_7(self):
        """
        Version 7 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()
        self.config["default_ssh_usernames"] = {}

    def _update_8(self):
        """
        Version 8 configuration update.

        Do not call.
        """
        self.config["editor_command"] = "nano {0}"

    def _update_9(self):
        """
        Version 9 configuration update.

        Do not call.
        """
        self.config["keypair_associations"] = {}

    def _update_10(self):
        """
        Version 10 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()

    def _update_11(self):
        """
        Version 11 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()

    def _update_12(self):
        """
        Version 12 configuration update.

        Do not call.
        """
        self.config["log_retention"] = {
            "max_lines": -1,
            "max_age": 2419200,
        }

    def _update_13(self):
        """
        Version 13 configuration update.

        Do not call.
        """
        self.config["default_dashboard_layout"] = [
            ["Blank", "Blank"],
            ["Blank", "Blank"],
        ]
        self.config["dashboard_layouts"] = {}
        self.scheme.backup_and_reset()

    def _update_14(self):
        """
        Version 14 configuration update.

        Do not call.
        """
        self.config["contexts"]["localstack"] = {
            "endpoint_url": "https://localhost.localstack.cloud"
        }

    def _update_15(self):
        """
        Version 15 configuration update.

        Do not call.
        """
        self.config["contexts"]["localstack"]["account_id"] = "localhost"

    def _update_16(self):
        """
        Version 16 configuration update.

        Do not call.
        """
        self.config["contexts"]["localstack"][
            "endpoint_url"
        ] = "https://localhost.localstack.cloud:4566"

    def _update_17(self):
        """
        Version 17 configuration update.

        Do not call.
        """
        for context in self.config["contexts"].keys():
            self.config["contexts"][context]["mfa_device"] = ""

    def _update_18(self):
        """
        Version 18 configuration update.

        Do not call.
        """
        error_path = Path.home() / ".config" / "awsc" / "error.log"
        self.config["error_log"] = str(error_path)

    def _update_19(self):
        """
        Version 19 configuration update.

        Do not call.
        """
        for context in self.config["contexts"].keys():
            self.config["contexts"][context]["role"] = ""

    def update_version(self):
        """
        Main configuration update sequence. Always called by initialize(), not required to call separately.
        """
        if "version" not in self.config:
            version = 0
        else:
            version = self.config["version"]
        while version < LAST_CONFIG_VERSION:
            print(f"Performing config update to version {version + 1}")
            self.version_updaters[version + 1]()
            version += 1
        self.config["version"] = version
        self.write_config()

    def create_default_config(self):
        """
        Generates first time default configuration. Should match the expected format of the latest update version.

        Writes the generated configuration to the configuration file in config_path.
        """
        print("Creating first time configuration...")
        error_path = Path.home() / ".config" / "awsc" / "error.log"
        self.config = {
            "version": LAST_CONFIG_VERSION,
            "contexts": {
                "localstack": {
                    "endpoint_url": "https://localhost.localstack.cloud:4566",
                    "account_id": "localhost",
                }
            },
            "default_context": "",
            "default_region": "us-east-1",
            "default_ssh_key": "id_rsa",
            "default_ssh_usernames": {},
            "keypair_associations": {},
            "editor_command": "nano {0}",
            "log_retention": {
                "max_lines": -1,
                "max_age": 2419200,
            },
            "usage_statistics": {
                "regions": {},
                "resources": {},
                "keys": {},
            },
            "default_dashboard_layout": [["Blank", "Blank"], ["Blank", "Blank"]],
            "dashboard_layouts": {},
            "error_log": str(error_path),
        }

        self.write_config()

    def write_config(self):
        """
        Immediately writes the configuration to the configuration file in config_path.
        """
        with self.config_path.open("w", encoding="utf-8") as file:
            file.write(yaml.dump(self.config))

    def __contains__(self, item):
        return item in self.config

    def __getitem__(self, item):
        """
        Retrieve a configuration value.

        Parameters
        ----------
        item : str
            The configuration key.

        Returns
        -------
        object
            The configuration value.
        """
        return self.config[item]

    def __setitem__(self, item, value):
        """
        Set a configuration value.

        Parameters
        ----------
        item : str
            The configuration key.
        value : object
            The configuration value.
        """
        self.config[item] = value

    def parse_config(self):
        """
        Parses the configuration file specified in config_path and replaces the currently loaded config with its contents.
        """
        with self.config_path.open("r", encoding="utf-8") as file:
            self.config = yaml.safe_load(file.read())

    def add_or_edit_context(self, name, acctid, access, secret, mfa_device=""):
        """
        Upserts a context into the configuration.

        Parameters
        ----------
        name : str
            The name of the context. If it already exists, it will be overwritten.
        acctid : str
            The account number of the context, usually acquired through Common.Session.whoami()
        access : str
            The access key which belongs to the account.
        secret : str
            The secret key which belongs to the account.
        """
        self.config["contexts"][name] = {
            "account_id": acctid,
            "mfa_device": mfa_device,
            "role": "",
        }
        if self.config["default_context"] == "":
            self.config["default_context"] = name
        self.keystore.set_key(name, access, secret)
        self.write_config()

    def add_or_edit_role_context(self, name, acctid, source, role, mfa_device=""):
        """
        Upserts a context into the configuration.

        Parameters
        ----------
        name : str
            The name of the context. If it already exists, it will be overwritten.
        acctid : str
            The account number of the context, usually acquired through Common.Session.whoami()
        access : str
            The access key which belongs to the account.
        secret : str
            The secret key which belongs to the account.
        """
        self.config["contexts"][name] = {
            "account_id": acctid,
            "mfa_device": mfa_device,
            "role": role,
        }
        self.keystore.set_ref(name, source)
        self.write_config()

    def delete_context(self, name):
        """
        Deletes a context from the configuration.

        Parameters
        ----------
        name : str
            The name of the context.
        """
        del self.config["contexts"][name]
        if self.config["default_context"] == name:
            if len(self.config["contexts"]):
                self.config["default_context"] = list(self.config["contexts"].keys())[0]
        self.keystore.delete_key(name)
        self.write_config()
