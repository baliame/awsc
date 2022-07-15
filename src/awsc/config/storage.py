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
    def __init__(self, config):
        self.keylist_file = config.path / "keys"
        p = getpass.getpass("Enter encryption phrase for key database: ")
        sha = hashlib.sha256(p.encode("ascii"))
        self.nonce_file = config.path / "nonce"
        if not self.nonce_file.exists():
            self.nonce = os.urandom(16)
            with self.nonce_file.open("wb") as f:
                f.write(self.nonce)
        else:
            with self.nonce_file.open("rb") as f:
                self.nonce = f.read()
        self.keylist_cipher = Cipher(AES(sha.digest()), CBC(self.nonce))

        if not self.keylist_file.exists():
            self.keys = {}
        else:
            self.parse_keylist()

    def parse_keylist(self):
        try:
            with self.keylist_file.open("rb") as f:
                data = f.read()
            dec = self.keylist_cipher.decryptor()
            yd = dec.update(data) + dec.finalize()
            unpadder = PKCS7(256).unpadder()
            yd = unpadder.update(yd) + unpadder.finalize()
            self.keys = yaml.safe_load(yd.decode("UTF-8"))
        except ValueError:
            print("Incorrect password.")
            sys.exit(1)

    def write_keylist(self):
        enc = self.keylist_cipher.encryptor()
        yd = yaml.dump(self.keys).encode("UTF-8")
        padder = PKCS7(256).padder()
        padded = padder.update(yd) + padder.finalize()
        data = enc.update(padded) + enc.finalize()
        with self.keylist_file.open("wb") as f:
            f.write(data)

    def __getitem__(self, item):
        return self.keys[item]

    def set_key(self, name, access, secret):
        self.keys[name] = {"access": access, "secret": secret}
        self.write_keylist()

    def delete_key(self, name):
        del self.keys[name]
        self.write_keylist()
