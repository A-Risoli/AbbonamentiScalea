"""Bot settings dialog for configuring Telegram bot."""

import asyncio

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)
from telegram import Bot

from abbonamenti.bot.config import BotConfig
from abbonamenti.gui.styles import get_stylesheet
from abbonamenti.utils.autostart import set_autostart_enabled


class BotSettingsDialog(QDialog):
    """Dialog for configuring Telegram bot settings."""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = BotConfig.load_config()
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Impostazioni Bot Telegram")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setStyleSheet(get_stylesheet())

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Info label
        info_label = QLabel(
            "Configura il bot Telegram per verificare le targhe da remoto."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Telegram settings group
        telegram_group = QGroupBox("Configurazione Telegram")
        telegram_layout = QFormLayout(telegram_group)
        telegram_layout.setSpacing(12)

        # Enable checkbox
        self.enable_checkbox = QCheckBox("Abilita bot Telegram")
        telegram_layout.addRow("Stato:", self.enable_checkbox)

        # Autostart checkbox
        self.autostart_checkbox = QCheckBox(
            "Avvia bot all'avvio del PC (in background)"
        )
        telegram_layout.addRow("Avvio automatico:", self.autostart_checkbox)

        # Token input (password field)
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("Bot token da @BotFather")
        telegram_layout.addRow("Token Bot *:", self.token_input)

        # Expiring threshold
        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(1, 30)
        self.threshold_spinbox.setValue(7)
        self.threshold_spinbox.setSuffix(" giorni")
        telegram_layout.addRow("Soglia scadenza:", self.threshold_spinbox)

        # Allowed users
        users_label = QLabel(
            "Inserisci gli User ID Telegram autorizzati, uno per riga.\n"
            "Gli agenti possono ottenere il proprio ID inviando /myid al bot."
        )
        users_label.setWordWrap(True)
        users_label.setStyleSheet("color: #666; font-size: 11px;")
        telegram_layout.addRow(users_label)

        self.users_input = QPlainTextEdit()
        self.users_input.setPlaceholderText("123456789\n987654321")
        self.users_input.setMaximumHeight(100)
        telegram_layout.addRow("User ID autorizzati:", self.users_input)

        layout.addWidget(telegram_group)

        # Test connection button
        test_button = QPushButton("Testa Connessione")
        test_button.clicked.connect(self.test_connection)
        test_button.setMinimumHeight(36)
        layout.addWidget(test_button)

        # Spacer
        layout.addStretch()

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Annulla")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Salva")
        save_btn.setMinimumHeight(36)
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self.save_settings)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def load_settings(self):
        """Load settings from config."""
        self.enable_checkbox.setChecked(self.config.enabled)
        self.autostart_checkbox.setChecked(self.config.autostart_enabled)

        # Load decrypted token
        token = self.config.get_decrypted_token()
        self.token_input.setText(token)

        self.threshold_spinbox.setValue(self.config.expiring_threshold_days)

        # Load user IDs (one per line)
        user_ids_text = "\n".join(str(uid) for uid in self.config.allowed_user_ids)
        self.users_input.setPlainText(user_ids_text)

    def save_settings(self):
        """Save settings to config."""
        # Validate token first if bot is being enabled
        bot_enabled = self.enable_checkbox.isChecked()
        token = self.token_input.text().strip()
        
        if bot_enabled and not token:
            QMessageBox.warning(
                self,
                "Token mancante",
                "Se abiliti il bot, devi inserire un token valido.",
            )
            return
        
        if bot_enabled and token and ":" not in token:
            # Validate token format (basic check - should contain colon)
            QMessageBox.warning(
                self,
                "Formato token non valido",
                "Il token Telegram dovrebbe avere il formato: <bot_id>:<token_string>\n"
                "Esempio: 8284695109:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh\n\n"
                "Ottieni un token valido da @BotFather su Telegram.",
            )
            return

        # Parse user IDs first to validate them
        user_ids_text = self.users_input.toPlainText()
        user_ids = []
        for line in user_ids_text.split("\n"):
            line = line.strip()
            if line and line.isdigit():
                user_ids.append(int(line))

        if bot_enabled and not user_ids:
            QMessageBox.warning(
                self,
                "User ID mancanti",
                "Se abiliti il bot, devi inserire almeno uno User ID Telegram autorizzato.",
            )
            return

        # Update config
        self.config.enabled = bot_enabled

        # Encrypt and save token
        self.config.set_encrypted_token(token)

        # Verify encryption worked if token is being set
        if token and not self.config.token_encrypted:
            QMessageBox.critical(
                self,
                "Errore crittografia",
                "Impossibile crittografare il token.\n\n"
                "Verifica che le chiavi di crittografia siano configurate correttamente.",
            )
            return

        self.config.expiring_threshold_days = self.threshold_spinbox.value()
        self.config.allowed_user_ids = user_ids

        # Handle autostart
        self.config.autostart_enabled = self.autostart_checkbox.isChecked()
        success, error_msg = set_autostart_enabled(self.config.autostart_enabled)
        if not success:
            QMessageBox.critical(
                self,
                "Errore avvio automatico",
                "Impossibile aggiornare l'avvio automatico.\n\n"
                f"Dettagli: {error_msg}",
            )
            return

        # Save to file - this is critical
        try:
            self.config.save_config()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Errore salvataggio configurazione",
                f"Impossibile salvare la configurazione.\n\n"
                f"Errore: {str(e)}",
            )
            return

        # Show success message
        status_msg = "✓ Configurazione bot salvata con successo."
        if bot_enabled:
            status_msg += "\n\nIl bot verrà riavviato con le nuove impostazioni."
        else:
            status_msg += "\n\nBot disabilitato."
            
        QMessageBox.information(
            self,
            "Impostazioni salvate",
            status_msg,
        )

        # Emit signal for main window to restart bot
        self.settings_changed.emit()

        # Accept dialog
        self.accept()

    def test_connection(self):
        """Test bot connection with current token."""
        token = self.token_input.text().strip()

        if not token:
            QMessageBox.warning(
                self, "Token mancante", "Inserisci un token per testare la connessione."
            )
            return

        # Test connection in async context
        try:
            # Create new event loop for this test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def test():
                bot = Bot(token=token)
                me = await bot.get_me()
                return me.username

            username = loop.run_until_complete(test())
            loop.close()

            QMessageBox.information(
                self,
                "Connessione riuscita",
                f"✅ Connessione riuscita!\n\nBot: @{username}",
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Errore di connessione",
                f"❌ Impossibile connettersi al bot.\n\nErrore: {e!s}",
            )
