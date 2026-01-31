"""Standalone CLI entry point for Telegram bot."""

import logging
import sys

from abbonamenti.bot.config import BotConfig
from abbonamenti.bot.handlers import (
    check_handler,
    handle_message,
    initialize_handlers,
    myid_handler,
)
from abbonamenti.bot.logger import BotQueryLogger
from abbonamenti.bot.rate_limiter import RateLimiter
from abbonamenti.database.manager import DatabaseManager
from abbonamenti.utils.paths import get_database_path, get_keys_dir

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for standalone bot."""
    print("AbbonaMunicipale - Telegram Bot")
    print("=" * 50)

    # Load configuration
    config = BotConfig.load_config()

    if not config.enabled:
        print("❌ Bot non abilitato nella configurazione.")
        print("   Avvia l'applicazione GUI e configura il bot in Strumenti > Impostazioni Bot")
        sys.exit(1)

    token = config.get_decrypted_token()
    if not token:
        print("❌ Token bot non configurato.")
        print("   Avvia l'applicazione GUI e configura il bot in Strumenti > Impostazioni Bot")
        sys.exit(1)

    print(f"✓ Configurazione caricata")
    print(f"  - Soglia scadenza: {config.expiring_threshold_days} giorni")
    print(f"  - Rate limit: {config.rate_limit_per_minute} richieste/minuto")
    print(f"  - Utenti autorizzati: {len(config.allowed_user_ids)}")

    # Initialize database manager
    try:
        db_path = get_database_path()
        keys_dir = get_keys_dir()
        db_manager = DatabaseManager(db_path, keys_dir)
        print(f"✓ Database connesso: {db_path}")
    except Exception as e:
        print(f"❌ Errore connessione database: {e}")
        sys.exit(1)

    # Initialize rate limiter and logger
    rate_limiter = RateLimiter(
        max_requests=config.rate_limit_per_minute, window_seconds=60
    )
    query_logger = BotQueryLogger()
    print(f"✓ Logger inizializzato: {query_logger.log_path}")

    # Initialize handlers
    initialize_handlers(db_manager, rate_limiter, query_logger)

    # Build and run application
    try:
        from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

        updater = Updater(token=token, use_context=True)
        dispatcher = updater.dispatcher

        # Add command handlers
        dispatcher.add_handler(CommandHandler("myid", myid_handler))
        dispatcher.add_handler(CommandHandler("check", check_handler))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

        print("✓ Bot inizializzato")
        print("\nComandi disponibili:")
        print("  /myid  - Mostra il tuo User ID Telegram")
        print("  /check <targa> - Verifica validità abbonamento")
        print("\n🚀 Bot in esecuzione... (Ctrl+C per terminare)\n")

        # Run polling (blocking)
        updater.start_polling(allowed_updates=["message"])
        updater.idle()

    except KeyboardInterrupt:
        print("\n\n⏹️ Bot arrestato dall'utente")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Errore fatale: {e}")
        logger.exception("Errore durante l'esecuzione del bot")
        sys.exit(1)


if __name__ == "__main__":
    main()
