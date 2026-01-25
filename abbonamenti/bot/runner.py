"""Bot runner thread for integrating asyncio with PyQt6."""

import asyncio
import logging

from PyQt6.QtCore import QThread, pyqtSignal
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from abbonamenti.bot.config import BotConfig
from abbonamenti.bot.handlers import (
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
    """QThread for running Telegram bot with asyncio event loop."""

    # Signals for GUI updates
    status_changed = pyqtSignal(str)  # "running", "stopped", "error"
    error_occurred = pyqtSignal(str)  # Error message

    def __init__(self, config: BotConfig):
        """
        Initialize bot thread.

        Args:
            config: Bot configuration
        """
        super().__init__()
        self.config = config
        self.application = None
        self.loop = None
        self._stop_requested = False

    def run(self) -> None:
        """Run the bot in a separate thread with asyncio event loop."""
        try:
            # Create new asyncio event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Initialize database manager (must be in same thread as SQLite usage)
            db_path = get_database_path()
            keys_dir = get_keys_dir()
            db_manager = DatabaseManager(db_path, keys_dir)

            # Initialize rate limiter and logger
            rate_limiter = RateLimiter(
                max_requests=self.config.rate_limit_per_minute, window_seconds=60
            )
            query_logger = BotQueryLogger()

            # Initialize handlers with dependencies
            initialize_handlers(db_manager, rate_limiter, query_logger)

            # Get decrypted token
            token = self.config.get_decrypted_token()
            if not token:
                self.error_occurred.emit("Token bot non configurato")
                self.status_changed.emit("error")
                return

            # Build application
            self.application = ApplicationBuilder().token(token).build()

            # Add command handlers
            self.application.add_handler(CommandHandler("start", start_handler))
            self.application.add_handler(CommandHandler("myid", myid_handler))
            self.application.add_handler(CommandHandler("help", help_handler))

            # Add message handler for direct text input (non-command)
            # Must be added AFTER CommandHandlers so commands are processed first
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            )

            # Emit running status
            self.status_changed.emit("running")
            logger.info("Bot Telegram avviato")

            # Run polling (blocking call)
            self.application.run_polling(allowed_updates=["message"])

        except Exception as e:
            error_msg = f"Errore bot: {e!s}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.status_changed.emit("error")

        finally:
            self.status_changed.emit("stopped")
            logger.info("Bot Telegram arrestato")

            # Clean up event loop
            if self.loop and self.loop.is_running():
                self.loop.stop()

    def stop(self) -> None:
        """Stop the bot gracefully."""
        self._stop_requested = True

        if self.application:
            try:
                # Stop and shutdown the application
                if self.loop and not self.loop.is_closed():
                    # Schedule stop in the event loop
                    asyncio.run_coroutine_threadsafe(
                        self.application.stop(), self.loop
                    )
                    asyncio.run_coroutine_threadsafe(
                        self.application.shutdown(), self.loop
                    )
            except Exception as e:
                logger.error(f"Errore durante l'arresto del bot: {e}")

        # Stop event loop
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
