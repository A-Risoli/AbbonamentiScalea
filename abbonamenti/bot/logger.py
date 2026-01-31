"""Bot query logger for tracking license plate checks."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from abbonamenti.utils.paths import get_app_data_dir


class BotQueryLogger:
    """Logs bot queries to JSONL file for external analysis."""

    def __init__(self):
        self.log_path = self._get_log_path()

    @staticmethod
    def _get_log_path() -> Path:
        """Get the path to the bot queries log file."""
        log_dir = get_app_data_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "bot_queries.log"

    def log_query(
        self,
        telegram_user_id: int,
        telegram_username: Optional[str],
        plate_searched: str,
        result_status: str,
        response_time_ms: float,
    ) -> None:
        """
        Log a bot query to the JSONL file.

        Args:
            telegram_user_id: Telegram user ID who made the query
            telegram_username: Telegram username (may be None)
            plate_searched: The license plate that was searched
            result_status: Result status (valid/expiring/not_found)
            response_time_ms: Query response time in milliseconds
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "telegram_user_id": telegram_user_id,
                "telegram_username": telegram_username or "",
                "plate_searched": plate_searched,
                "result_status": result_status,
                "response_time_ms": round(response_time_ms, 2),
            }

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            # Silently fail - logging should not break the bot
            pass
