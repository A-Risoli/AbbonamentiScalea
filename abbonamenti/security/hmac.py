import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes, hmac


class HMACManager:
    def __init__(self, keys_dir: Path):
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self._hmac_key: bytes = self._load_or_generate_key()

    def _load_or_generate_key(self) -> bytes:
        hmac_key_path = self.keys_dir / "hmac_key.bin"

        if hmac_key_path.exists():
            with open(hmac_key_path, "rb") as f:
                return f.read()

        hmac_key = os.urandom(32)
        with open(hmac_key_path, "wb") as f:
            f.write(hmac_key)
        return hmac_key

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
