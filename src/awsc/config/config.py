"""
Module for the configuration parser object.
"""
from pathlib import Path

import yaml

from .scheme import Scheme
from .storage import Keystore

LAST_CONFIG_VERSION = 12


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
        print("Initializing AWSC configuration...")
        self.version_updaters = {
            1: self.update_1,
            2: self.update_2,
            3: self.update_3,
            4: self.update_4,
            5: self.update_5,
            6: self.update_6,
            7: self.update_7,
            8: self.update_8,
            9: self.update_9,
            10: self.update_10,
            11: self.update_11,
            12: self.update_12,
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

    def update_1(self):
        """
        Version 1 configuration update.

        Do not call.
        """
        self.config["default_region"] = "us-east-1"

    def update_2(self):
        """
        Version 2 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()

    def update_3(self):
        """
        Version 3 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()

    def update_4(self):
        """
        Version 4 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()
        self.config["usage_statistics"] = {
            "regions_by_context": {},
            "resources_by_context": {},
        }

    def update_5(self):
        """
        Version 5 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()

    def update_6(self):
        """
        Version 6 configuration update.

        Do not call.
        """
        self.config["default_ssh_key"] = "id_rsa"

    def update_7(self):
        """
        Version 7 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()
        self.config["default_ssh_usernames"] = {}

    def update_8(self):
        """
        Version 8 configuration update.

        Do not call.
        """
        self.config["editor_command"] = "nano {0}"

    def update_9(self):
        """
        Version 9 configuration update.

        Do not call.
        """
        self.config["keypair_associations"] = {}

    def update_10(self):
        """
        Version 10 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()

    def update_11(self):
        """
        Version 11 configuration update.

        Do not call.
        """
        self.scheme.backup_and_reset()

    def update_12(self):
        """
        Version 12 configuration update.

        Do not call.
        """
        self.config["log_retention"] = {
            "max_lines": -1,
            "max_age": 2419200,
        }

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
        self.config = {
            "version": LAST_CONFIG_VERSION,
            "contexts": {},
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
        }

        self.write_config()

    def write_config(self):
        """
        Immediately writes the configuration to the configuration file in config_path.
        """
        with self.config_path.open("w", encoding="utf-8") as file:
            file.write(yaml.dump(self.config))

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

    def add_or_edit_context(self, name, acctid, access, secret):
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
        }
        if self.config["default_context"] == "":
            self.config["default_context"] = name
        self.keystore.set_key(name, access, secret)
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
                self.config["default_context"] = self.config["contexts"].keys()[0]
        self.keystore.delete_key(name)
        self.write_config()
