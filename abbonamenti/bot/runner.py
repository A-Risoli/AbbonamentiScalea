"""Bot runner thread for integrating asyncio with PyQt6."""

import asyncio
import logging

from PyQt6.QtCore import QThread, pyqtSignal
from telegram.error import NetworkError
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
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
            # Note: Timeout is handled through requests.Request via HTTP pool
            self.application = (
                ApplicationBuilder()
                .token(token)
                .build()
            )

            # Add command handlers
            self.application.add_handler(CommandHandler("start", start_handler))
            self.application.add_handler(CommandHandler("myid", myid_handler))
            self.application.add_handler(CommandHandler("help", help_handler))

            # Add callback query handler for inline buttons
            self.application.add_handler(CallbackQueryHandler(button_callback_handler))

            # Add message handler for direct text input (non-command)
            # Must be added AFTER CommandHandlers so commands are processed first
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            )

            # Emit running status
            self.status_changed.emit("running")
            logger.info("Bot Telegram avviato")

            # Run polling (blocking call) - include callback_query updates
            try:
                self.application.run_polling(
                    allowed_updates=["message", "callback_query"],
                    drop_pending_updates=False,
                )
            except NetworkError as e:
                # Log network errors but don't treat as critical during shutdown
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

            # Clean up event loop
            if self.loop and self.loop.is_running():
                self.loop.stop()

    def stop(self) -> None:
        """Stop the bot gracefully."""
        self._stop_requested = True

        if self.application:
            try:
                # Stop the application properly
                if self.loop and not self.loop.is_closed():
                    # Schedule stop and shutdown in the event loop
                    future = asyncio.run_coroutine_threadsafe(
                        self.application.stop(), self.loop
                    )
                    try:
                        # Wait for stop to complete (up to 5 seconds)
                        future.result(timeout=5)
                    except Exception as e:
                        logger.debug(f"Errore durante stop: {e}")

                    # Schedule shutdown
                    future = asyncio.run_coroutine_threadsafe(
                        self.application.shutdown(), self.loop
                    )
                    try:
                        # Wait for shutdown to complete (up to 5 seconds)
                        future.result(timeout=5)
                    except Exception as e:
                        logger.debug(f"Errore durante shutdown: {e}")
            except Exception as e:
                logger.debug(f"Errore durante l'arresto del bot: {e}")

        # Stop event loop
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
