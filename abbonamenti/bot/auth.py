"""Authorization decorator for bot handlers."""

from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from abbonamenti.bot.config import BotConfig


def require_authorized(func):
    """
    Decorator to require authorization for bot command handlers.

    Checks if the user's Telegram ID is in the allowed_user_ids list.
    If not authorized, sends "⛔ Accesso Negato" message.

    Usage:
        @require_authorized
        async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Handler code here
    """

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Load config to get allowed user IDs
        config = BotConfig.load_config()

        # Get user ID from update
        user_id = update.effective_user.id if update.effective_user else None

        # Check authorization
        if user_id not in config.allowed_user_ids:
            if update.message:
                await update.message.reply_text("⛔ Accesso Negato")
            return

        # User is authorized, proceed with handler
        return await func(update, context)

    return wrapper
