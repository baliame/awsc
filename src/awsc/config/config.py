from pathlib import Path

import yaml

from .scheme import Scheme
from .storage import Keystore

last_config_version = 12


class Config:
    def __init__(self, path=None):
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
        self.update_version()

    def update_1(self):
        self.config["default_region"] = "us-east-1"

    def update_2(self):
        self.scheme.backup_and_reset()

    def update_3(self):
        self.scheme.backup_and_reset()

    def update_4(self):
        self.scheme.backup_and_reset()
        self.config["usage_statistics"] = {
            "regions_by_context": {},
            "resources_by_context": {},
        }

    def update_5(self):
        self.scheme.backup_and_reset()

    def update_6(self):
        self.config["default_ssh_key"] = "id_rsa"

    def update_7(self):
        self.scheme.backup_and_reset()
        self.config["default_ssh_usernames"] = {}

    def update_8(self):
        self.config["editor_command"] = "nano {0}"

    def update_9(self):
        self.config["keypair_associations"] = {}

    def update_10(self):
        self.scheme.backup_and_reset()

    def update_11(self):
        self.scheme.backup_and_reset()

    def update_12(self):
        self.config["log_retention"] = {
            "max_lines": -1,
            "max_age": 2419200,
        }

    # TODO: Weigh whether it's worth implementing fshook (may be potentially dangerous)
    def update_X(self):
        self.config["editor_use_fshook"] = False

    def update_version(self):
        if "version" not in self.config:
            version = 0
        else:
            version = self.config["version"]
        while version < last_config_version:
            print("Performing config update to version {0}".format(version + 1))
            self.version_updaters[version + 1]()
            version += 1
        self.config["version"] = version
        self.write_config()

    def create_default_config(self):
        print("Creating first time configuration...")
        self.config = {
            "version": last_config_version,
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
        with self.config_path.open("w") as f:
            f.write(yaml.dump(self.config))

    def __getitem__(self, item):
        return self.config[item]

    def __setitem__(self, item, value):
        self.config[item] = value

    def parse_config(self):
        with self.config_path.open("r") as f:
            self.config = yaml.safe_load(f.read())

    def add_or_edit_context(self, name, acctid, access, secret):
        self.config["contexts"][name] = {
            "account_id": acctid,
        }
        if self.config["default_context"] == "":
            self.config["default_context"] = name
        self.keystore.set_key(name, access, secret)
        self.write_config()

    def delete_context(self, name):
        del self.config["contexts"][name]
        if self.config["default_context"] == name:
            if len(self.config["contexts"]):
                self.config["default_context"] = self.config["contexts"].keys()[0]
        self.keystore.delete_key(name)
        self.write_config()
