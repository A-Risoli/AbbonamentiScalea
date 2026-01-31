"""Bot runner thread for integrating Telegram bot with PyQt5."""

import logging
import time

from PyQt5.QtCore import QThread, pyqtSignal
from telegram.error import NetworkError
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from abbonamenti.bot.config import BotConfig
from abbonamenti.bot.handlers import (
    button_callback_handler,
    handle_message,
    help_handler,
    initialize_handlers,
    myid_handler,
    start_handler,
)
from abbonamenti.bot.logger import BotQueryLogger
from abbonamenti.bot.rate_limiter import RateLimiter
from abbonamenti.database.manager import DatabaseManager
from abbonamenti.utils.paths import get_database_path, get_keys_dir

logger = logging.getLogger(__name__)


class BotThread(QThread):
    """QThread for running Telegram bot with polling."""

    status_changed = pyqtSignal(str)  # "running", "stopped", "error"
    error_occurred = pyqtSignal(str)  # Error message

    def __init__(self, config: BotConfig):
        super().__init__()
        self.config = config
        self.updater = None
        self._stop_requested = False

    def run(self) -> None:
        """Run the bot in a separate thread with polling."""
        try:
            db_path = get_database_path()
            keys_dir = get_keys_dir()
            db_manager = DatabaseManager(db_path, keys_dir)

            rate_limiter = RateLimiter(
                max_requests=self.config.rate_limit_per_minute, window_seconds=60
            )
            query_logger = BotQueryLogger()

            initialize_handlers(db_manager, rate_limiter, query_logger)

            token = self.config.get_decrypted_token()
            if not token:
                self.error_occurred.emit("Token bot non configurato")
                self.status_changed.emit("error")
                return

            self.updater = Updater(token=token, use_context=True)
            dispatcher = self.updater.dispatcher

            dispatcher.add_handler(CommandHandler("start", start_handler))
            dispatcher.add_handler(CommandHandler("myid", myid_handler))
            dispatcher.add_handler(CommandHandler("help", help_handler))
            dispatcher.add_handler(CallbackQueryHandler(button_callback_handler))
            dispatcher.add_handler(
                MessageHandler(Filters.text & ~Filters.command, handle_message)
            )

            self.status_changed.emit("running")
            logger.info("Bot Telegram avviato")

            try:
                self.updater.start_polling(
                    allowed_updates=["message", "callback_query"],
                    drop_pending_updates=False,
                )

                while not self._stop_requested:
                    time.sleep(0.2)
            except NetworkError as e:
                logger.debug(f"Errore di rete durante il polling: {e}")
                if not self._stop_requested:
                    error_msg = f"Errore rete bot: {e!s}"
                    logger.error(error_msg)
                    self.error_occurred.emit(error_msg)
                    self.status_changed.emit("error")
                    raise

        except Exception as e:
            error_msg = f"Errore bot: {e!s}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.status_changed.emit("error")

        finally:
            self.status_changed.emit("stopped")
            logger.info("Bot Telegram arrestato")

    def stop(self) -> None:
        """Stop the bot gracefully."""
        self._stop_requested = True
        if self.updater:
            try:
                self.updater.stop()
            except Exception as e:
                logger.debug(f"Errore durante l'arresto del bot: {e}")
