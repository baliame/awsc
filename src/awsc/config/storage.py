"""
Module for the encrypted key store object.
"""
import datetime
import getpass
import hashlib
import os
import sys

import yaml
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC
from cryptography.hazmat.primitives.padding import PKCS7


class Keystore:
    """
    Encrypted key storage for AWS credentials.

    Attributes
    ----------
    keylist_file : pathlib.Path
        Encrypted binary which stores the AWS credentials.
    nonce_file : pathlib.Path
        Nonce file for the encryption.
    nonce : bytes
        The nonce value.
    keylist_cipher : cryptography.hazmat.primitives.cipher.Cipher
        The cryptography cipher used to decrypt and encrypt the key storage.
    keys : dict
        A list of decrypted key pairs, keyed by account name.
    """

    def __init__(self, config):
        """
        Initializes a Keystore object.

        Parameters
        ----------
        config : awsc.config.config.Configuration
            The parent configuration object instance.
        """
        self.keylist_file = config.path / "keys"
        self.nonce_file = config.path / "nonce"
        self.keylist_cipher = None
        self.nonce = os.urandom(16)
        self.keys = {}

    def do_unlock(self, password):
        """
        Unlock keystore with a password.
        """
        sha = hashlib.sha256(password.encode("ascii"))
        if not self.nonce_file.exists():
            with self.nonce_file.open("wb") as file:
                file.write(self.nonce)
        else:
            with self.nonce_file.open("rb") as file:
                self.nonce = file.read()
        self.keylist_cipher = Cipher(AES(sha.digest()), CBC(self.nonce))

        if self.keylist_file.exists():
            self.parse_keylist()

    def unlock(self, silent=False):
        """
        Prompts the user to enter the password to access the key storage, and parses the keylist file.
        """
        password = getpass.getpass(
            "Enter encryption phrase for key database: ",
            stream=sys.stderr if silent else None,
        )
        self.do_unlock(password)

    def parse_keylist(self):
        """
        Attempts to parse the keylist file.

        Should be called through unlock(), as unlock() generates the cipher for this method.
        """
        try:
            with self.keylist_file.open("rb") as file:
                data = file.read()
            dec = self.keylist_cipher.decryptor()
            yaml_decoded = dec.update(data) + dec.finalize()
            unpadder = PKCS7(256).unpadder()
            yaml_decoded = unpadder.update(yaml_decoded) + unpadder.finalize()
            self.keys = yaml.safe_load(yaml_decoded.decode("UTF-8"))
            changed = False
            for key in self.keys:
                if "temp" in self.keys[key]:
                    changed = True
                    self.keys[key].pop("temp")
            if changed:
                self.write_keylist()
        except ValueError:
            print("Incorrect password.")
            sys.exit(1)

    def write_keylist(self):
        """
        Writes the keylist to the keylist_file. Cipher must be loaded through unlock() before writing.
        """
        enc = self.keylist_cipher.encryptor()
        yaml_encoded = yaml.dump(self.keys).encode("UTF-8")
        padder = PKCS7(256).padder()
        padded = padder.update(yaml_encoded) + padder.finalize()
        data = enc.update(padded) + enc.finalize()
        with self.keylist_file.open("wb") as file:
            file.write(data)

    def __getitem__(self, item):
        """
        Returns the named keypair. Resolves references unless temporary credentials are available.

        Parameters
        ----------
        item : str
            Name of the keypair to fetch.

        Returns
        -------
        dict
            A dict containing the access and secret keys.
        """
        while key := self.keys[item]:
            if "temp" in key:
                if (
                    datetime.datetime.fromtimestamp(key["temp"]["expiry"])
                    > datetime.datetime.now()
                ):
                    return key["temp"]
            if "ref" in key:
                item = key["ref"]
                continue
            return key

    def force_resolve(self, item):
        """
        Returns the named keypair. Resolves references and ignored temporary credentials.

        Parameters
        ----------
        item : str
            Name of the keypair to fetch.

        Returns
        -------
        dict
            A dict containing the access and secret keys.
        """
        while key := self.keys[item]:
            if "ref" in key:
                item = key["ref"]
                continue
            if "temp" in key:
                if (
                    datetime.datetime.fromtimestamp(key["temp"]["expiry"])
                    > datetime.datetime.now()
                ):
                    return key["temp"]
            return key

    def get_permanent_credentials(self, item):
        """
        Returns the permanent credentials associated with a context.

        Parameters
        ----------
        item : str
            Name of the key..

        Returns
        -------
        dict
            Gets the permanent credentials associated with a context.
        """
        while key := self.keys[item]:
            if "ref" in key:
                item = key["ref"]
                continue
            return key

    def get_ref_name(self, item):
        """
        Returns the ref of the named keypair, as this property is not accessible through __getitem__.

        Parameters
        ----------
        item: str
            Name of the key with a reference.

        Returns
        -------
        str | None
            Name of the key being referenced, or None if none.
        """
        key = self.keys[item]
        return key["ref"] if "ref" in key else None

    def get_all_ref_targets(self):
        """
        Enumerates all ref targets into a list.

        Returns
        -------
        set(str)
            A list of keys which are targets of refs.
        """
        targets = set()
        for key in self.keys:
            if "ref" in key:
                targets.add(key["ref"])
        return targets

    def __contains__(self, item):
        return item in self.keys

    def set_key(self, name, access, secret):
        """
        Upserts a key into the key storage and writes to disk.

        Parameters
        ----------
        name : str
            The name of the keypair.
        access : str
            The access key of the keypair.
        secret : str
            The secret key of the keypair.
        """
        self.keys[name] = {"access": access, "secret": secret}
        self.write_keylist()

    def set_ref(self, name, ref):
        """
        Upserts a reference key into the key storage and writes to disk.

        Parameters
        ----------
        name : str
            The name of the keypair.
        ref : str
            The target keypair being referenced.
        """
        self.keys[name] = {"ref": ref}
        self.write_keylist()

    def set_temp(self, name, data):
        """
        Sets temporary credentials for a reference key.

        Parameters
        ----------
        name : str
            The name of the keypair.
        data : dict
            The temporary data of the keypair.
        """
        self.keys[name]["temp"] = data
        self.write_keylist()

    def delete_key(self, name):
        """
        Deletes a key from the key storage and writes to disk.

        Parameters
        ----------
        name : str
            The name of the key to delete.
        """
        del self.keys[name]
        self.write_keylist()
