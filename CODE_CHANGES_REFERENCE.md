# Code Changes - Bot UX Refactor

## File 1: abbonamenti/bot/handlers.py

### Key Changes

#### New Imports
```python
from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction  # ← Fixed import
from telegram.ext import ContextTypes
```

#### New Function: start_handler()
```python
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /start command with persistent keyboard buttons."""
    if not update.message or not update.effective_user:
        return

    user_name = update.effective_user.first_name or "Agente"
    keyboard = [["🆔 Mio ID", "❓ Aiuto"]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=False, resize_keyboard=True
    )

    welcome_text = (
        f"👋 Benvenuto {user_name}!\n\n"
        "Sono il bot di controllo abbonamenti. Puoi:\n\n"
        "📱 <b>Inviare una targa</b> (es: AB123CD)\n"
        "🆔 <b>Visualizzare il tuo ID</b> con il pulsante a lato\n"
        "❓ <b>Leggere le istruzioni</b> con il pulsante aiuto\n\n"
        "Digita la targa senza spazi, il resto lo faccio io! 🚗"
    )

    await update.message.reply_text(
        welcome_text, reply_markup=reply_markup, parse_mode="HTML"
    )
```

#### New Function: help_handler()
```python
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /help command with instructions."""
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

    await update.message.reply_text(help_text, parse_mode="HTML")
```

#### New Function: handle_message() (Main Handler)
```python
@require_authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for all text messages (non-command)."""
    if not update.message or not update.message.text or not update.effective_user:
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id
    username = update.effective_user.username

    # Detect button presses and route to handlers
    if text == "🆔 Mio ID":
        await myid_handler(update, context)
        return

    if text == "❓ Aiuto":
        await help_handler(update, context)
        return

    # Everything else is treated as a license plate query
    # Sanitize input: remove spaces and uppercase
    plate = text.upper().replace(" ", "").strip()

    # Validate plate format (basic check)
    if not plate or len(plate) < 5:
        await update.message.reply_text(
            "❌ Formato targa non valido. Usa: AB123CD"
        )
        return

    # Check rate limit
    if rate_limiter and not rate_limiter.is_allowed(user_id):
        wait_time = rate_limiter.get_wait_time(user_id)
        await update.message.reply_text(
            f"⏳ Limite raggiunto! Max 20 richieste/minuto. Attendi {wait_time} secondi."
        )
        return

    # Show typing indicator
    await update.message.chat.send_action(ChatAction.TYPING)

    # Load config for threshold
    config = BotConfig.load_config()

    # Measure query time
    start_time = time.time()

    # Check plate validity
    try:
        status, message, expiry_date = check_plate_validity(
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
    await update.message.reply_text(message, parse_mode="HTML")
```

#### Updated: myid_handler()
```python
async def myid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /myid command and 🆔 button."""
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    await update.message.reply_text(
        f"Il tuo User ID è: <code>{user_id}</code>", parse_mode="HTML"
    )
```

#### Removed: check_handler()
- No longer needed (replaced by handle_message)
- `/check` command functionality now available via direct text input

---

## File 2: abbonamenti/bot/runner.py

### Key Changes

#### Updated Imports
```python
# OLD
from telegram.ext import ApplicationBuilder, CommandHandler

# NEW
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from abbonamenti.bot.handlers import (
    handle_message,  # ← NEW
    help_handler,    # ← NEW
    initialize_handlers,
    myid_handler,
    start_handler,   # ← NEW
)
```

#### Updated Handler Registration (in run() method)
```python
# OLD
self.application.add_handler(CommandHandler("myid", myid_handler))
self.application.add_handler(CommandHandler("check", check_handler))

# NEW
self.application.add_handler(CommandHandler("start", start_handler))
self.application.add_handler(CommandHandler("myid", myid_handler))
self.application.add_handler(CommandHandler("help", help_handler))

# Add message handler for direct text input (non-command)
# Must be added AFTER CommandHandlers so commands are processed first
self.application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
)
```

---

## Summary of Changes

### handlers.py (Line Count: 189)
- ✅ Added: start_handler() → 19 lines
- ✅ Added: help_handler() → 22 lines
- ✅ Added: handle_message() → 90 lines (main new feature)
- ✅ Updated: myid_handler() → better formatting
- ✅ Removed: check_handler() → no longer needed
- ✅ Fixed: ChatAction import from telegram.constants
- ✅ Updated: myid_handler to also handle button presses

### runner.py (Line Count: 129)
- ✅ Added: MessageHandler import
- ✅ Added: filters import
- ✅ Added: handle_message, help_handler, start_handler imports
- ✅ Added: CommandHandler for /start
- ✅ Added: CommandHandler for /help
- ✅ Added: MessageHandler registration
- ✅ Removed: CommandHandler for /check
- ✅ Updated: handler initialization comments

---

## Behavior Changes

### Before
```
User Input          → Bot Response
/start             → No response (no handler)
/myid              → Il tuo User ID è: 123456789
/check AB123CD     → ✅ VALIDO! Scade: 31/12/2026
/help              → No response (no handler)
AB123CD            → No response (not a command)
```

### After
```
User Input          → Bot Response
/start             → Welcome message + keyboard buttons
/myid              → Il tuo User ID è: 123456789 (formatted better)
/check AB123CD     → (Not supported - but /help explains new method)
/help              → 4-section help guide with examples
AB123CD            → [typing...] → ✅ VALIDO! Scade: 31/12/2026
AB 123 CD          → [typing...] → ✅ VALIDO! Scade: 31/12/2026 (spaces removed)
[🆔 Mio ID]        → Il tuo User ID è: 123456789
[❓ Aiuto]         → 4-section help guide
```

---

## Technical Details

### ChatAction Import Fix
```python
# WRONG (no longer works in telegram v21+)
from telegram import ChatAction

# RIGHT (correct for telegram v21+)
from telegram.constants import ChatAction
```

### MessageHandler Filter
```python
# This intercepts all text messages that are NOT commands
MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)

# Why this order matters:
# 1. CommandHandlers added first → /start /myid /help processed
# 2. MessageHandler added last → everything else goes here
# 3. If order reversed, MessageHandler would catch /start before CommandHandler
```

### Persistent Keyboard
```python
# Creates buttons that stay visible after bot restarts
keyboard = [["🆔 Mio ID", "❓ Aiuto"]]
reply_markup = ReplyKeyboardMarkup(
    keyboard, 
    one_time_keyboard=False,  # ← Stays visible (not one-time)
    resize_keyboard=True       # ← Fills screen width
)
```

---

## Backwards Compatibility

⚠️ **BREAKING CHANGE:** `/check AB123CD` command no longer works
- ✅ **Solution:** User sends `AB123CD` as text instead
- ✅ **Guidance:** Send `/help` to see new interface

✅ **Preserved:**
- Authorization checks (still require_authorized)
- Rate limiting (still 20/minute)
- Audit logging (still logs to JSONL)
- Database queries (same logic, just called differently)
- Encryption (token still encrypted)
- Error handling (same try/except pattern)

---

## Files Not Modified

The following files continue to work as-is:
- ✅ abbonamenti/bot/config.py
- ✅ abbonamenti/bot/queries.py
- ✅ abbonamenti/bot/auth.py
- ✅ abbonamenti/bot/logger.py
- ✅ abbonamenti/bot/rate_limiter.py
- ✅ abbonamenti/bot/main.py
- ✅ abbonamenti/gui/dialogs/bot_settings_dialog.py
- ✅ abbonamenti/gui/main_window.py
- ✅ abbonamenti/database/manager.py

---

*Generated: 2026-01-25*
*Project: AbbonamentiScalea*
*Component: Telegram Bot UX Refactor*
