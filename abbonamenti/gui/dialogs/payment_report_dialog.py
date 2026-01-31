"""Payment Report Dialog for selecting period and generating PDF reports."""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from abbonamenti.database.manager import DatabaseManager
from abbonamenti.gui.styles import get_color, get_stylesheet


class StatCard(QWidget):
    """Widget for displaying a single statistic"""

    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #757575; font-size: 11px;")
        layout.addWidget(title_label)

        # Value - store reference for updates
        self.value_label = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(20)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        self.value_label.setStyleSheet(f"color: {get_color('primary')};")
        layout.addWidget(self.value_label)

        # Style the card
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {get_color('card_bg')};
                border: 1px solid {get_color('border')};
                border-radius: 8px;
            }}
            QWidget:hover {{
                border-color: {get_color('primary')};
            }}
            """
        )

    def update_value(self, value: str):
        """Update the displayed value"""
        self.value_label.setText(value)


class PaymentReportDialog(QDialog):
    """Dialog for configuring and generating payment PDF reports"""

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_file_path: Optional[Path] = None
        self.init_ui()
        # Set default to current month and load preview
        self.month_radio.setChecked(True)
        self.update_date_widgets()
        self.update_preview()

    def init_ui(self):
        self.setWindowTitle("📄 Genera Report PDF Pagamenti")
        self.setMinimumSize(700, 600)
        self.setStyleSheet(get_stylesheet())

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Header
        header_label = QLabel("Genera Report Abbonamenti e Incassi")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setStyleSheet(f"color: {get_color('primary')};")
        main_layout.addWidget(header_label)

        # Description
        desc_label = QLabel(
            "Seleziona il periodo per generare un report PDF con statistiche aggregate "
            "(totale abbonamenti, incassi, e metodi di pagamento)."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #757575; font-size: 12px;")
        main_layout.addWidget(desc_label)

        # Period selection group
        period_group = QGroupBox("Tipo di Periodo")
        period_group.setStyleSheet(
            f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {get_color('border')};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }}
            """
        )
        period_layout = QVBoxLayout(period_group)
        period_layout.setSpacing(12)

        # Radio buttons for period type
        self.day_radio = QRadioButton("Giorno")
        self.week_radio = QRadioButton("Settimana (ISO)")
        self.month_radio = QRadioButton("Mese")
        self.year_radio = QRadioButton("Anno")

        self.period_group = QButtonGroup()
        self.period_group.addButton(self.day_radio, 0)
        self.period_group.addButton(self.week_radio, 1)
        self.period_group.addButton(self.month_radio, 2)
        self.period_group.addButton(self.year_radio, 3)

        # Connect radio buttons to update date widgets
        self.day_radio.toggled.connect(self.update_date_widgets)
        self.week_radio.toggled.connect(self.update_date_widgets)
        self.month_radio.toggled.connect(self.update_date_widgets)
        self.year_radio.toggled.connect(self.update_date_widgets)

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.day_radio)
        radio_layout.addWidget(self.week_radio)
        radio_layout.addWidget(self.month_radio)
        radio_layout.addWidget(self.year_radio)
        period_layout.addLayout(radio_layout)

        # Date picker container
        self.date_container = QWidget()
        self.date_layout = QHBoxLayout(self.date_container)
        self.date_layout.setContentsMargins(0, 0, 0, 0)

        # Day picker
        self.day_label = QLabel("Data:")
        self.day_picker = QDateEdit()
        self.day_picker.setCalendarPopup(True)
        self.day_picker.setDate(datetime.now().date())
        self.day_picker.setDisplayFormat("dd/MM/yyyy")
        self.day_picker.dateChanged.connect(self.update_preview)

        # Week picker
        self.week_label = QLabel("Settimana:")
        self.week_spinner = QSpinBox()
        self.week_spinner.setRange(1, 53)
        self.week_spinner.setValue(datetime.now().isocalendar()[1])
        self.week_spinner.valueChanged.connect(self.update_preview)

        self.week_year_label = QLabel("Anno:")
        self.week_year_spinner = QSpinBox()
        self.week_year_spinner.setRange(2020, 2100)
        self.week_year_spinner.setValue(datetime.now().year)
        self.week_year_spinner.valueChanged.connect(self.update_preview)

        # Month picker
        self.month_label = QLabel("Mese:")
        self.month_combo = QComboBox()
        months = [
            "Gennaio",
            "Febbraio",
            "Marzo",
            "Aprile",
            "Maggio",
            "Giugno",
            "Luglio",
            "Agosto",
            "Settembre",
            "Ottobre",
            "Novembre",
            "Dicembre",
        ]
        self.month_combo.addItems(months)
        self.month_combo.setCurrentIndex(datetime.now().month - 1)
        self.month_combo.currentIndexChanged.connect(self.update_preview)

        self.month_year_label = QLabel("Anno:")
        self.month_year_spinner = QSpinBox()
        self.month_year_spinner.setRange(2020, 2100)
        self.month_year_spinner.setValue(datetime.now().year)
        self.month_year_spinner.valueChanged.connect(self.update_preview)

        # Year picker
        self.year_label = QLabel("Anno:")
        self.year_spinner = QSpinBox()
        self.year_spinner.setRange(2020, 2100)
        self.year_spinner.setValue(datetime.now().year)
        self.year_spinner.valueChanged.connect(self.update_preview)

        # Add all pickers to layout (will show/hide based on selection)
        self.date_layout.addWidget(self.day_label)
        self.date_layout.addWidget(self.day_picker)
        self.date_layout.addWidget(self.week_label)
        self.date_layout.addWidget(self.week_spinner)
        self.date_layout.addWidget(self.week_year_label)
        self.date_layout.addWidget(self.week_year_spinner)
        self.date_layout.addWidget(self.month_label)
        self.date_layout.addWidget(self.month_combo)
        self.date_layout.addWidget(self.month_year_label)
        self.date_layout.addWidget(self.month_year_spinner)
        self.date_layout.addWidget(self.year_label)
        self.date_layout.addWidget(self.year_spinner)
        self.date_layout.addStretch()

        period_layout.addWidget(self.date_container)

        # Week info label
        self.week_info_label = QLabel("")
        self.week_info_label.setStyleSheet("color: #757575; font-size: 11px;")
        self.week_info_label.setWordWrap(True)
        period_layout.addWidget(self.week_info_label)

        main_layout.addWidget(period_group)

        # Preview section
        preview_label = QLabel("Anteprima Dati")
        preview_font = QFont()
        preview_font.setBold(True)
        preview_label.setFont(preview_font)
        main_layout.addWidget(preview_label)

        # Preview cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.total_card = StatCard("Totale Incassi", "0.00 €")
        self.count_card = StatCard("N° Abbonamenti", "0")
        self.average_card = StatCard("Media", "0.00 €")

        cards_layout.addWidget(self.total_card)
        cards_layout.addWidget(self.count_card)
        cards_layout.addWidget(self.average_card)

        main_layout.addLayout(cards_layout)

        # Payment methods preview
        methods_layout = QHBoxLayout()
        methods_layout.setSpacing(12)

        self.pos_card = StatCard("POS", "0")
        self.bollettino_card = StatCard("Bollettino", "0")

        methods_layout.addWidget(self.pos_card)
        methods_layout.addWidget(self.bollettino_card)

        main_layout.addLayout(methods_layout)

        main_layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        cancel_btn = QPushButton("Annulla")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.clicked.connect(self.reject)

        generate_btn = QPushButton("📄 Genera PDF")
        generate_btn.setMinimumHeight(38)
        generate_btn.setMinimumWidth(150)
        generate_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {get_color('primary')};
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #1565c0;
            }}
            """
        )
        generate_btn.clicked.connect(self.generate_report)

        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(generate_btn)

        main_layout.addLayout(button_layout)

    def update_date_widgets(self):
        """Show/hide date widgets based on selected period type"""
        # Hide all first
        self.day_label.hide()
        self.day_picker.hide()
        self.week_label.hide()
        self.week_spinner.hide()
        self.week_year_label.hide()
        self.week_year_spinner.hide()
        self.month_label.hide()
        self.month_combo.hide()
        self.month_year_label.hide()
        self.month_year_spinner.hide()
        self.year_label.hide()
        self.year_spinner.hide()
        self.week_info_label.hide()

        # Show relevant widgets
        if self.day_radio.isChecked():
            self.day_label.show()
            self.day_picker.show()
        elif self.week_radio.isChecked():
            self.week_label.show()
            self.week_spinner.show()
            self.week_year_label.show()
            self.week_year_spinner.show()
            self.week_info_label.show()
            self.update_week_info()
        elif self.month_radio.isChecked():
            self.month_label.show()
            self.month_combo.show()
            self.month_year_label.show()
            self.month_year_spinner.show()
        elif self.year_radio.isChecked():
            self.year_label.show()
            self.year_spinner.show()

        self.update_preview()

    def update_week_info(self):
        """Update the week info label with date range"""
        try:
            year = self.week_year_spinner.value()
            week = self.week_spinner.value()
            # Get Monday of the ISO week
            monday = datetime.fromisocalendar(year, week, 1)
            sunday = monday + timedelta(days=6)
            self.week_info_label.setText(
                f"Settimana {week} ({monday.strftime('%d/%m/%Y')} - "
                f"{sunday.strftime('%d/%m/%Y')})"
            )
        except (ValueError, AttributeError):
            self.week_info_label.setText("")

    def get_date_range(self) -> tuple[datetime, datetime, str, str]:
        """
        Get the date range based on selected period.

        Returns:
            Tuple of (date_from, date_to, period_type, period_label)
        """
        if self.day_radio.isChecked():
            selected_date = self.day_picker.date().toPyDate()
            date_from = datetime.combine(selected_date, datetime.min.time())
            date_to = datetime.combine(selected_date, datetime.max.time())
            period_type = "Giorno"
            period_label = selected_date.strftime("%d/%m/%Y")
        elif self.week_radio.isChecked():
            year = self.week_year_spinner.value()
            week = self.week_spinner.value()
            monday = datetime.fromisocalendar(year, week, 1)
            sunday = monday + timedelta(days=6)
            date_from = datetime.combine(monday.date(), datetime.min.time())
            date_to = datetime.combine(sunday.date(), datetime.max.time())
            period_type = "Settimana"
            period_label = (
                f"Settimana {week} ({monday.strftime('%d/%m/%Y')} - "
                f"{sunday.strftime('%d/%m/%Y')})"
            )
        elif self.month_radio.isChecked():
            year = self.month_year_spinner.value()
            month = self.month_combo.currentIndex() + 1
            # First day of month
            date_from = datetime(year, month, 1, 0, 0, 0)
            # Last day of month
            if month == 12:
                date_to = datetime(year, 12, 31, 23, 59, 59)
            else:
                date_to = datetime(year, month + 1, 1, 0, 0, 0) - timedelta(seconds=1)
            period_type = "Mese"
            period_label = f"{self.month_combo.currentText()} {year}"
        else:  # year
            year = self.year_spinner.value()
            date_from = datetime(year, 1, 1, 0, 0, 0)
            date_to = datetime(year, 12, 31, 23, 59, 59)
            period_type = "Anno"
            period_label = str(year)

        return date_from, date_to, period_type, period_label

    def update_preview(self):
        """Update the preview cards with filtered statistics"""
        try:
            date_from, date_to, _, _ = self.get_date_range()

            # Update week info if week is selected
            if self.week_radio.isChecked():
                self.update_week_info()

            # Debug: print the date range being used
            print(f"DEBUG update_preview: date_from={date_from.isoformat()}, date_to={date_to.isoformat()}")

            # Get filtered statistics
            stats = self.db_manager.get_payment_statistics(
                date_from=date_from, date_to=date_to
            )

            # Debug: print the stats returned
            print(f"DEBUG stats: {stats}")

            # Update cards
            self.total_card.update_value(f"{stats['total_revenue']:.2f} €")
            self.count_card.update_value(str(stats["subscription_count"]))
            if stats["subscription_count"] > 0:
                self.average_card.update_value(f"{stats['average_payment']:.2f} €")
            else:
                self.average_card.update_value("0.00 €")

            self.pos_card.update_value(str(stats["pos_count"]))
            self.bollettino_card.update_value(str(stats["bollettino_count"]))

        except Exception as e:
            print(f"Error updating preview: {e}")

    def generate_filename(self) -> str:
        """Generate suggested filename based on period selection"""
        if self.day_radio.isChecked():
            selected_date = self.day_picker.date().toPyDate()
            return f"report_pagamenti_{selected_date.strftime('%Y-%m-%d')}.pdf"
        elif self.week_radio.isChecked():
            year = self.week_year_spinner.value()
            week = self.week_spinner.value()
            return f"report_pagamenti_{year}-W{week:02d}.pdf"
        elif self.month_radio.isChecked():
            year = self.month_year_spinner.value()
            month = self.month_combo.currentIndex() + 1
            return f"report_pagamenti_{year}-{month:02d}.pdf"
        else:  # year
            year = self.year_spinner.value()
            return f"report_pagamenti_{year}.pdf"

    def generate_report(self):
        """Generate the PDF report"""
        try:
            # Get file path from user
            suggested_filename = self.generate_filename()
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Salva Report PDF",
                suggested_filename,
                "File PDF (*.pdf)",
            )

            if not file_path:
                return

            # Ensure .pdf extension
            if not file_path.endswith(".pdf"):
                file_path += ".pdf"

            self.selected_file_path = Path(file_path)

            # Get statistics for the selected period
            date_from, date_to, period_type, period_label = self.get_date_range()
            stats = self.db_manager.get_payment_statistics(
                date_from=date_from, date_to=date_to
            )

            # Calculate revenue by payment method
            subs = self.db_manager._get_subscriptions_for_stats(date_from, date_to)
            pos_revenue = sum(
                sub["payment_details"]
                for sub in subs
                if self.db_manager._normalize_payment_method(
                    sub.get("payment_method", "")
                )
                == "POS"
            )
            bollettino_revenue = sum(
                sub["payment_details"]
                for sub in subs
                if self.db_manager._normalize_payment_method(
                    sub.get("payment_method", "")
                )
                == "BOLLETTINO"
            )

            # Store the data for the parent to use
            self.stats = stats
            self.pos_revenue = pos_revenue
            self.bollettino_revenue = bollettino_revenue
            self.period_type = period_type
            self.period_label = period_label

            # Accept the dialog
            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Errore",
                f"Errore durante la generazione del report:\n{str(e)}",
            )
