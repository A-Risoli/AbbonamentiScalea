"""Bot configuration management with encrypted token storage."""

import base64
import json
from pathlib import Path

from abbonamenti.security.crypto import CryptoManager
from abbonamenti.utils.paths import get_app_data_dir, get_keys_dir


class BotConfig:
    """Manages bot configuration with encrypted token storage."""

    def __init__(self):
        self.enabled = False
        self.token_encrypted = ""
        self.allowed_user_ids: list[int] = []
        self.expiring_threshold_days = 7
        self.rate_limit_per_minute = 20

    @staticmethod
    def get_config_path() -> Path:
        """Get the path to the bot configuration file."""
        config_dir = get_app_data_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "bot_settings.json"

    @staticmethod
    def load_config() -> "BotConfig":
        """Load configuration from JSON file."""
        config = BotConfig()
        config_path = BotConfig.get_config_path()

        if not config_path.exists():
            return config

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)

            config.enabled = data.get("enabled", False)
            config.token_encrypted = data.get("token_encrypted", "")
            config.allowed_user_ids = data.get("allowed_user_ids", [])
            config.expiring_threshold_days = data.get("expiring_threshold_days", 7)
            config.rate_limit_per_minute = data.get("rate_limit_per_minute", 20)
        except Exception:
            # Silently fail and return defaults
            pass

        return config

    def save_config(self) -> None:
        """Save configuration to JSON file."""
        try:
            config_path = BotConfig.get_config_path()
            data = {
                "enabled": self.enabled,
                "token_encrypted": self.token_encrypted,
                "allowed_user_ids": self.allowed_user_ids,
                "expiring_threshold_days": self.expiring_threshold_days,
                "rate_limit_per_minute": self.rate_limit_per_minute,
            }

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Silently fail - not critical
            pass

    def get_decrypted_token(self) -> str:
        """Decrypt and return the bot token."""
        if not self.token_encrypted:
            return ""

        try:
            keys_dir = get_keys_dir()
            crypto_manager = CryptoManager(keys_dir)
            token_bytes = base64.b64decode(self.token_encrypted)
            # decrypt returns str directly
            return crypto_manager.decrypt(token_bytes)
        except Exception:
            return ""

    def set_encrypted_token(self, token: str) -> None:
        """Encrypt and store the bot token."""
        if not token:
            self.token_encrypted = ""
            return

        try:
            keys_dir = get_keys_dir()
            # Ensure keys directory exists
            keys_dir.mkdir(parents=True, exist_ok=True)
            crypto_manager = CryptoManager(keys_dir)
            # CryptoManager.encrypt expects str, not bytes
            encrypted = crypto_manager.encrypt(token)
            self.token_encrypted = base64.b64encode(encrypted).decode("utf-8")
        except Exception as e:
            # Log error for debugging but don't crash
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Errore durante la crittografia del token: {e}")
            self.token_encrypted = ""
            self.token_encrypted = ""
