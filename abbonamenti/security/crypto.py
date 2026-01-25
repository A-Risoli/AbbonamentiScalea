import json
import os
import base64
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    PublicFormat,
)


class CryptoManager:
    def __init__(self, keys_dir: Path):
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self._fernet: Fernet = self._load_or_generate_fernet_key()
        self._hmac_key: bytes = self._load_or_generate_hmac_key()

    def _load_or_generate_fernet_key(self) -> Fernet:
        fernet_key_path = self.keys_dir / "fernet_key.bin"

        if fernet_key_path.exists():
            with open(fernet_key_path, "rb") as f:
                fernet_key = f.read()
        else:
            fernet_key = Fernet.generate_key()
            with open(fernet_key_path, "wb") as f:
                f.write(fernet_key)

        return Fernet(fernet_key)

    def _load_or_generate_hmac_key(self) -> bytes:
        hmac_key_path = self.keys_dir / "hmac_key.bin"

        if hmac_key_path.exists():
            with open(hmac_key_path, "rb") as f:
                return f.read()

        hmac_key = os.urandom(32)
        with open(hmac_key_path, "wb") as f:
            f.write(hmac_key)
        return hmac_key

    def encrypt(self, data: str) -> bytes:
        return self._fernet.encrypt(data.encode("utf-8"))

    def decrypt(self, encrypted_data: bytes) -> str:
        return self._fernet.decrypt(encrypted_data).decode("utf-8")

    def generate_hmac(self, data: dict) -> bytes:
        data_str = json.dumps(data, sort_keys=True)
        h = hmac.HMAC(self._hmac_key, hashes.SHA256())
        h.update(data_str.encode("utf-8"))
        return h.finalize()

    def verify_hmac(self, data: dict, signature: bytes) -> bool:
        try:
            data_str = json.dumps(data, sort_keys=True)
            h = hmac.HMAC(self._hmac_key, hashes.SHA256())
            h.update(data_str.encode("utf-8"))
            h.verify(signature)
            return True
        except Exception:
            return False


def derive_key_from_passphrase(passphrase: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """
    Derive a 32-byte encryption key from a passphrase using PBKDF2.
    
    Args:
        passphrase: User passphrase (minimum 16 characters)
        salt: Optional salt (if None, generates new random salt)
        
    Returns:
        Tuple of (derived_key, salt)
        
    Raises:
        ValueError: If passphrase is less than 16 characters
    """
    if len(passphrase) < 16:
        raise ValueError("Passphrase deve essere di almeno 16 caratteri")
    
    if salt is None:
        salt = os.urandom(32)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=1000000,
    )
    
    key = kdf.derive(passphrase.encode('utf-8'))
    return key, salt


def encrypt_with_key(data: bytes, key: bytes) -> bytes:
    """Encrypt data with a derived key using Fernet."""
    fernet_key = base64.urlsafe_b64encode(key)
    fernet = Fernet(fernet_key)
    return fernet.encrypt(data)


def decrypt_with_key(encrypted_data: bytes, key: bytes) -> bytes:
    """Decrypt data with a derived key using Fernet."""
    fernet_key = base64.urlsafe_b64encode(key)
    fernet = Fernet(fernet_key)
    return fernet.decrypt(encrypted_data)


class KeyManager:
    def __init__(self, keys_dir: Path):
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self._private_key: rsa.RSAPrivateKey = self._load_or_generate_keys()[0]
        self._public_key: rsa.RSAPublicKey = self._load_or_generate_keys()[1]

    def _load_or_generate_keys(self) -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        private_key_path = self.keys_dir / "private_key.pem"
        public_key_path = self.keys_dir / "public_key.pem"

        if private_key_path.exists() and public_key_path.exists():
            with open(private_key_path, "rb") as f:
                private_pem = f.read()
                private_key = serialization.load_pem_private_key(
                    private_pem, password=None
                )
                assert isinstance(private_key, rsa.RSAPrivateKey)

            with open(public_key_path, "rb") as f:
                public_pem = f.read()
                public_key = serialization.load_pem_public_key(public_pem)
                assert isinstance(public_key, rsa.RSAPublicKey)

            return private_key, public_key

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_pem = public_key.public_bytes(
            encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo
        )

        with open(private_key_path, "wb") as f:
            f.write(private_pem)

        with open(public_key_path, "wb") as f:
            f.write(public_pem)

        return private_key, public_key

    def sign_data(self, data: str) -> bytes:
        signature = self._private_key.sign(
            data.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
        return signature

    def verify_signature(self, data: str, signature: bytes) -> bool:
        try:
            self._public_key.verify(
                signature,
                data.encode("utf-8"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False
