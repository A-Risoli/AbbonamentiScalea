from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa, serialization
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


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
            encryption_algorithm=NoEncryption(),
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
