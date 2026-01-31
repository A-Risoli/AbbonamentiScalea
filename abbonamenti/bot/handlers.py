"""Telegram bot command and message handlers."""

import logging
import time
from typing import Optional

from telegram import ChatAction, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from abbonamenti.bot.auth import require_authorized
from abbonamenti.bot.config import BotConfig
from abbonamenti.bot.logger import BotQueryLogger
from abbonamenti.bot.queries import check_plate_validity
from abbonamenti.bot.rate_limiter import RateLimiter
from abbonamenti.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

# Global instances (will be set by runner)
db_manager: Optional[DatabaseManager] = None
rate_limiter: Optional[RateLimiter] = None
query_logger: Optional[BotQueryLogger] = None


def initialize_handlers(
    db: DatabaseManager, limiter: RateLimiter, logger_instance: BotQueryLogger
) -> None:
    """Initialize global handler dependencies."""
    global db_manager, rate_limiter, query_logger
    db_manager = db
    rate_limiter = limiter
    query_logger = logger_instance


def start_handler(update: Update, context: CallbackContext) -> None:
    """
    Handler for /start command.

    Shows welcome message with inline keyboard buttons.
    """
    if not update.message or not update.effective_user:
        return

    user_name = update.effective_user.first_name or "Agente"

    # Create inline keyboard (buttons appear directly below the message)
    keyboard = [
        [
            InlineKeyboardButton("🆔 Mio ID", callback_data="myid"),
            InlineKeyboardButton("❓ Aiuto", callback_data="help"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"👋 Benvenuto {user_name}!\n\n"
        "Sono il bot di controllo abbonamenti. Puoi:\n\n"
        "📱 <b>Inviare una targa</b> (es: AB123CD)\n"
        "🆔 <b>Visualizzare il tuo ID</b> con il pulsante qui sotto\n"
        "❓ <b>Leggere le istruzioni</b> con il pulsante aiuto\n\n"
        "Digita la targa senza spazi, il resto lo faccio io! 🚗"
    )

    update.message.reply_text(
        welcome_text, reply_markup=reply_markup, parse_mode="HTML"
    )


def myid_handler(update: Update, context: CallbackContext) -> None:
    """
    Handler for /myid command and 🆔 button.

    Returns the user's Telegram ID (no authorization required).
    This helps administrators onboard new authorized users.
    """
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    update.message.reply_text(
        f"Il tuo User ID è: <code>{user_id}</code>", parse_mode="HTML"
    )


def help_handler(update: Update, context: CallbackContext) -> None:
    """
    Handler for /help command and ❓ button.

    Shows comprehensive instructions for using the bot.
    """
    if not update.message:
        return

    help_text = (
        "📖 <b>COME USARE IL BOT</b>\n\n"
        "<b>1️⃣ Inviare una Targa</b>\n"
        "Digita la targa senza spazi:\n"
        "  • Valido: <code>AB123CD</code>\n"
        "  • Valido: <code>AB 123 CD</code> (spazi rimossi automaticamente)\n"
        "  • Invalido: <code>ABCD123</code> (formato sbagliato)\n\n"
        "<b>2️⃣ Risposta del Bot</b>\n"
        "✅ VALIDO - Abbonamento attivo\n"
        "⚠️ SCADE PRESTO - Scade nei prossimi 30 giorni\n"
        "❌ SCADUTO - Abbonamento non valido\n"
        "❓ NON TROVATO - Targa non in database\n\n"
        "<b>3️⃣ Limiti di Utilizzo</b>\n"
        "Max 20 richieste al minuto per utente\n"
        "Se raggiunto il limite, attendi prima di continuare\n\n"
        "<b>4️⃣ Il Tuo ID</b>\n"
        "Usa il pulsante 🆔 per scoprire il tuo User ID"
    )

    update.message.reply_text(help_text, parse_mode="HTML")


def button_callback_handler(update: Update, context: CallbackContext) -> None:
    """
    Handler for inline button callbacks.

    Routes button presses to appropriate handlers.
    """
    query = update.callback_query
    if not query:
        return

    # CRITICAL: Answer callback immediately to prevent timeout
    query.answer()
    
    logger.info(f"Button pressed: {query.data} by user {query.from_user.id if query.from_user else 'unknown'}")

    if query.data == "myid":
        # Show user ID
        if query.from_user:
            user_id = query.from_user.id
            query.message.reply_text(
                f"Il tuo User ID è: <code>{user_id}</code>", parse_mode="HTML"
            )
            logger.info(f"Sent user ID to {user_id}")
                
    elif query.data == "help":
        # Show help text
        help_text = (
            "📖 <b>COME USARE IL BOT</b>\n\n"
            "<b>1️⃣ Inviare una Targa</b>\n"
            "Digita la targa senza spazi:\n"
            "  • Valido: <code>AB123CD</code>\n"
            "  • Valido: <code>AB 123 CD</code> (spazi rimossi automaticamente)\n\n"
            "<b>2️⃣ Risposta del Bot</b>\n"
            "✅ VALIDO - Abbonamento attivo\n"
            "⚠️ SCADE PRESTO - Scade nei prossimi 30 giorni\n"
            "❌ SCADUTO - Abbonamento non valido\n"
            "❓ NON TROVATO - Targa non in database\n\n"
            "<b>3️⃣ Limiti di Utilizzo</b>\n"
            "Max 20 richieste al minuto per utente\n\n"
            "<b>4️⃣ Il Tuo ID</b>\n"
            "Usa il pulsante 🆔 per scoprire il tuo User ID"
        )
        query.message.reply_text(help_text, parse_mode="HTML")
        logger.info(f"Sent help to user {query.from_user.id if query.from_user else 'unknown'}")


def _process_plate_query(
    update: Update, plate: str, user_id: int, username: Optional[str]
) -> None:
    """Process a license plate query and reply to the user."""
    # Validate plate format (basic check)
    if not plate or len(plate) < 5:
        update.message.reply_text(
            "❌ Formato targa non valido. Usa: AB123CD"
        )
        return

    # Check rate limit
    if rate_limiter and not rate_limiter.is_allowed(user_id):
        wait_time = rate_limiter.get_wait_time(user_id)
        update.message.reply_text(
            f"⏳ Limite raggiunto! Max 20 richieste/minuto. Attendi {wait_time} secondi."
        )
        return

    # Show typing indicator
    update.message.chat.send_action(ChatAction.TYPING)

    # Load config for threshold
    config = BotConfig.load_config()

    # Measure query time
    start_time = time.time()

    # Check plate validity
    try:
        status, message, _ = check_plate_validity(
            db_manager, plate, config.expiring_threshold_days
        )
    except Exception as e:
        status = "error"
        message = f"❌ Errore durante la ricerca: {e!s}"
        logger.error(f"Errore in check_plate_validity: {e}", exc_info=True)

    # Calculate response time
    response_time_ms = (time.time() - start_time) * 1000

    # Log query
    if query_logger:
        query_logger.log_query(
            telegram_user_id=user_id,
            telegram_username=username,
            plate_searched=plate,
            result_status=status,
            response_time_ms=response_time_ms,
        )

    # Send response
    update.message.reply_text(message, parse_mode="HTML")


@require_authorized
def check_handler(update: Update, context: CallbackContext) -> None:
    """Handler for /check command with plate argument."""
    if not update.message or not update.message.text or not update.effective_user:
        return

    parts = update.message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        update.message.reply_text("Uso: /check TARGA")
        return

    plate = parts[1].upper().replace(" ", "").strip()
    user_id = update.effective_user.id
    username = update.effective_user.username
    _process_plate_query(update, plate, user_id, username)


@require_authorized
def handle_message(update: Update, context: CallbackContext) -> None:
    """
    Handler for all text messages (non-command).

    Processes license plate queries.
    Requires authorization for plate checks.
    """
    if not update.message or not update.message.text or not update.effective_user:
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id
    username = update.effective_user.username

    # Everything is treated as a license plate query
    plate = text.upper().replace(" ", "").strip()
    _process_plate_query(update, plate, user_id, username)
