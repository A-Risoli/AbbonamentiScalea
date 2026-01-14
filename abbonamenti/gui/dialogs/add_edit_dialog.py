from datetime import datetime, timedelta

from PyQt6.QtCore import QDate, Qt, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from abbonamenti.database.schema import Subscription
from abbonamenti.gui.styles import get_stylesheet, get_color


class AddEditSubscriptionDialog(QDialog):
    def __init__(self, parent=None, subscription: Subscription | None = None):
        super().__init__(parent)
        self.subscription = subscription
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(
            "Nuovo Abbonamento" if self.subscription is None else "Modifica Abbonamento"
        )
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)
        self.setStyleSheet(get_stylesheet())

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Scroll area for better UX with long forms
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)

        # Info Group
        info_group = QGroupBox("Informazioni Generali")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(10)

        self.protocol_input = QLineEdit()
        self.protocol_input.setReadOnly(True)
        self.protocol_input.setText(
            "Generato automaticamente"
            if self.subscription is None
            else self.subscription.protocol_id
        )
        self.protocol_input.setStyleSheet(
            f"background-color: {get_color('surface')}; color: {get_color('text_primary')};"
        )
        info_layout.addRow("ID Protocollo:", self.protocol_input)

        self.owner_input = QLineEdit()
        self.owner_input.setPlaceholderText("Inserisci nome completo...")
        if self.subscription:
            self.owner_input.setText(self.subscription.owner_name)
        info_layout.addRow("Nome Proprietario *:", self.owner_input)

        self.license_plate_input = QLineEdit()
        self.license_plate_input.setMaxLength(10)
        self.license_plate_input.setPlaceholderText("AA123BB")
        if self.subscription:
            self.license_plate_input.setText(self.subscription.license_plate)
        info_layout.addRow("Targa *:", self.license_plate_input)

        scroll_layout.addWidget(info_group)

        # Contact Group
        contact_group = QGroupBox("Dati di Contatto")
        contact_layout = QFormLayout(contact_group)
        contact_layout.setSpacing(10)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@esempio.com")
        if self.subscription:
            self.email_input.setText(self.subscription.email)
        contact_layout.addRow("Email:", self.email_input)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Via, numero, città...")
        if self.subscription:
            self.address_input.setText(self.subscription.address)
        contact_layout.addRow("Indirizzo:", self.address_input)

        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("+39 333 123 4567")
        if self.subscription:
            self.mobile_input.setText(self.subscription.mobile)
        contact_layout.addRow("Cellulare:", self.mobile_input)

        scroll_layout.addWidget(contact_group)

        # Dates Group
        dates_group = QGroupBox("Periodo di Validità")
        dates_layout = QFormLayout(dates_group)
        dates_layout.setSpacing(10)

        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDate(QDate.currentDate())
        if self.subscription:
            self.start_date_input.setDate(
                QDate.fromString(
                    self.subscription.subscription_start.strftime("%d/%m/%Y"),
                    "dd/MM/yyyy",
                )
            )
        dates_layout.addRow("Data Inizio *:", self.start_date_input)

        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        current_year = datetime.now().year
        self.end_date_input.setDate(QDate(current_year, 12, 31))
        if self.subscription:
            self.end_date_input.setDate(
                QDate.fromString(
                    self.subscription.subscription_end.strftime("%d/%m/%Y"),
                    "dd/MM/yyyy",
                )
            )
        dates_layout.addRow("Data Fine *:", self.end_date_input)

        scroll_layout.addWidget(dates_group)

        # Payment Group
        payment_group = QGroupBox("Informazioni Pagamento")
        payment_layout = QFormLayout(payment_group)
        payment_layout.setSpacing(10)

        self.payment_method_combo = QComboBox()
        self.payment_method_combo.addItems(["POS", "Bollettino"])
        if self.subscription:
            self.payment_method_combo.setCurrentText(self.subscription.payment_method)
        payment_layout.addRow("Metodo di Pagamento *:", self.payment_method_combo)

        self.payment_amount_input = QDoubleSpinBox()
        self.payment_amount_input.setRange(0.00, 999999.99)
        self.payment_amount_input.setDecimals(2)
        self.payment_amount_input.setSuffix(" €")
        self.payment_amount_input.setToolTip("Importo pagato in euro")
        if self.subscription:
            self.payment_amount_input.setValue(self.subscription.payment_details)
        payment_layout.addRow("Importo Pagato *:", self.payment_amount_input)

        scroll_layout.addWidget(payment_group)

        # Reason Group
        reason_group = QGroupBox("Motivo della Modifica")
        reason_layout = QVBoxLayout(reason_group)
        reason_layout.setSpacing(8)

        reason_label = QLabel("Descrivi il motivo della modifica (minimo 10 caratteri)")
        reason_label.setStyleSheet("color: #666; font-size: 11px;")
        reason_layout.addWidget(reason_label)

        self.reason_input = QLineEdit()
        if self.subscription:
            self.reason_input.setPlaceholderText(
                "Inserisci il motivo della modifica (min. 10 caratteri)"
            )
        else:
            self.reason_input.setText("Inserimento nuovo abbonamento")
        reason_layout.addWidget(self.reason_input)

        scroll_layout.addWidget(reason_group)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()

        cancel_button = QPushButton("Annulla")
        cancel_button.setMinimumHeight(36)
        cancel_button.setMinimumWidth(120)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton("Salva")
        save_button.setMinimumHeight(36)
        save_button.setMinimumWidth(120)
        save_button.setObjectName("successBtn")
        save_button.clicked.connect(self.save)
        button_layout.addWidget(save_button)

        main_layout.addLayout(button_layout)

    @pyqtSlot()
    def save(self):
        if not self.validate_input():
            return

        self.accept()

    def validate_input(self) -> bool:
        if not self.owner_input.text().strip():
            QMessageBox.warning(
                self, "Errore", "Il nome del proprietario è obbligatorio."
            )
            return False

        if not self.license_plate_input.text().strip():
            QMessageBox.warning(self, "Errore", "La targa è obbligatoria.")
            return False

        email_text = self.email_input.text().strip()
        if email_text and "@" not in email_text:
            QMessageBox.warning(self, "Errore", "Inserisci un'email valida.")
            return False

        if self.end_date_input.date() <= self.start_date_input.date():
            QMessageBox.warning(
                self,
                "Errore",
                "La data di fine deve essere successiva alla data di inizio.",
            )
            return False

        if self.payment_amount_input.value() <= 0:
            QMessageBox.warning(
                self,
                "Errore",
                "L'importo pagato deve essere maggiore di zero.",
            )
            return False

        reason = self.reason_input.text().strip()
        if len(reason) < 10:
            QMessageBox.warning(
                self,
                "Errore",
                "Il motivo deve contenere almeno 10 caratteri.",
            )
            return False

        return True

    def get_data(self) -> dict:
        return {
            "protocol_id": self.protocol_input.text(),
            "owner_name": self.owner_input.text().strip(),
            "license_plate": self.license_plate_input.text().strip().upper(),
            "email": self.email_input.text().strip(),
            "address": self.address_input.text().strip(),
            "mobile": self.mobile_input.text().strip(),
            "subscription_start": self.start_date_input.date().toPyDate(),
            "subscription_end": self.end_date_input.date().toPyDate(),
            "payment_details": self.payment_amount_input.value(),
            "payment_method": self.payment_method_combo.currentText(),
            "reason": self.reason_input.text().strip(),
        }


class DeleteSubscriptionDialog(QDialog):
    def __init__(self, parent=None, subscription: Subscription | None = None):
        super().__init__(parent)
        self.subscription = subscription
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Conferma Eliminazione")
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)
        self.setStyleSheet(get_stylesheet())

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Warning message
        warning_label = QLabel("⚠️  Attenzione!")
        warning_font = QFont()
        warning_font.setPointSize(12)
        warning_font.setBold(True)
        warning_label.setFont(warning_font)
        warning_label.setStyleSheet("color: #F44336;")
        main_layout.addWidget(warning_label)

        message_label = QLabel("Stai per eliminare questo abbonamento.")
        message_font = QFont()
        message_font.setPointSize(11)
        message_label.setFont(message_font)
        main_layout.addWidget(message_label)

        # Details group
        details_group = QGroupBox("Dettagli Abbonamento")
        details_layout = QVBoxLayout(details_group)
        details_layout.setSpacing(8)

        protocol_label = QLabel(f"<b>ID Protocollo:</b> {self.subscription.protocol_id}")
        details_layout.addWidget(protocol_label)

        owner_label = QLabel(f"<b>Nome Proprietario:</b> {self.subscription.owner_name}")
        details_layout.addWidget(owner_label)

        plate_label = QLabel(f"<b>Targa:</b> {self.subscription.license_plate}")
        details_layout.addWidget(plate_label)

        amount_label = QLabel(f"<b>Importo Pagato:</b> € {self.subscription.payment_details:.2f}")
        details_layout.addWidget(amount_label)

        main_layout.addWidget(details_group)

        # Reason group
        reason_group = QGroupBox("Motivo dell'Eliminazione")
        reason_layout = QVBoxLayout(reason_group)
        reason_layout.setSpacing(8)

        reason_description = QLabel("Descrivi il motivo dell'eliminazione (minimo 10 caratteri)")
        reason_description.setStyleSheet("color: #666; font-size: 11px;")
        reason_layout.addWidget(reason_description)

        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText(
            "Es: Richiesta del cliente, errore di inserimento, dati duplicati..."
        )
        reason_layout.addWidget(self.reason_input)

        main_layout.addWidget(reason_group)
        main_layout.addStretch()

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()

        cancel_button = QPushButton("Annulla")
        cancel_button.setMinimumHeight(36)
        cancel_button.setMinimumWidth(120)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        delete_button = QPushButton("🗑️  Elimina Definitivamente")
        delete_button.setMinimumHeight(36)
        delete_button.setMinimumWidth(180)
        delete_button.setObjectName("deleteBtn")
        delete_button.clicked.connect(self.delete)
        button_layout.addWidget(delete_button)

        main_layout.addLayout(button_layout)

    @pyqtSlot()
    def delete(self):
        reason = self.reason_input.text().strip()
        if len(reason) < 10:
            QMessageBox.warning(
                self,
                "Errore",
                "Il motivo deve contenere almeno 10 caratteri.",
            )
            return

        self.accept()

    def get_reason(self) -> str:
        return self.reason_input.text().strip()
