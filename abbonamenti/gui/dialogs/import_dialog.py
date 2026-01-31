"""Import dialog for bulk subscription imports from Excel files."""

import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from abbonamenti.utils.excel_parser import read_excel_file, validate_all_rows
from abbonamenti.utils.paths import get_app_data_dir


class ImportDialog(QDialog):
    """Dialog for importing subscriptions from Excel files."""

    import_completed = pyqtSignal(int)  # Emitted with count of imported records

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.excel_file_path = None
        self.excel_data = []
        self.validated_data = []

        self.setWindowTitle("Importa Abbonamenti da Excel")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self.init_ui()
        self.load_column_mappings()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # File selection section
        file_group = QGroupBox("1. Seleziona File Excel")
        file_layout = QHBoxLayout()

        self.file_path_label = QLabel("Nessun file selezionato")
        self.file_path_label.setWordWrap(True)
        file_layout.addWidget(self.file_path_label, 1)

        self.browse_button = QPushButton("Sfoglia...")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_button)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Column mapping section
        mapping_group = QGroupBox("2. Mappa Colonne Excel")
        mapping_layout = QFormLayout()

        self.column_combos = {}

        # Required fields
        required_fields = [
            ("owner_name", "Nome Proprietario *"),
            ("license_plate", "Targa *"),
            ("subscription_start", "Data Inizio *"),
            ("payment_details", "Importo *"),
        ]

        # Optional fields
        optional_fields = [
            ("email", "Email"),
            ("address", "Indirizzo"),
            ("mobile", "Cellulare"),
            ("subscription_end", "Data Fine"),
            ("pos", "POS"),
            ("bollettino", "Bollettino"),
        ]

        for field_id, field_label in required_fields + optional_fields:
            combo = QComboBox()
            combo.addItem("-- Non mappato --", "")
            combo.setMinimumWidth(200)
            self.column_combos[field_id] = combo
            mapping_layout.addRow(field_label + ":", combo)

        mapping_group.setLayout(mapping_layout)
        layout.addWidget(mapping_group)

        # Import reason section
        reason_group = QGroupBox("3. Motivo Importazione")
        reason_layout = QVBoxLayout()

        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText(
            "Inserisci motivo (minimo 10 caratteri)..."
        )
        reason_layout.addWidget(self.reason_input)

        reason_group.setLayout(reason_layout)
        layout.addWidget(reason_group)

        # Progress section
        progress_group = QGroupBox("4. Avanzamento")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Pronto per l'importazione")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # will be set after reading file
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.validate_button = QPushButton("Valida Dati")
        self.validate_button.clicked.connect(self.validate_data)
        self.validate_button.setEnabled(False)
        button_layout.addWidget(self.validate_button)

        self.import_button = QPushButton("Importa")
        self.import_button.clicked.connect(self.import_data)
        self.import_button.setEnabled(False)
        button_layout.addWidget(self.import_button)

        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def browse_file(self):
        """Open file browser to select Excel file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleziona File Excel",
            "",
            "File Excel (*.xlsx *.xls);;Tutti i file (*.*)",
        )

        if file_path:
            self.excel_file_path = file_path
            self.file_path_label.setText(file_path)
            self.load_excel_columns()
            self.validate_button.setEnabled(True)
            self.import_button.setEnabled(False)
            self.validated_data = []

            # Set default reason
            filename = Path(file_path).name
            today = datetime.now().strftime("%d/%m/%Y")
            self.reason_input.setText(f"Importazione Excel: {filename} {today}")

    def load_excel_columns(self):
        """Load column names from Excel file into combo boxes."""
        if not self.excel_file_path:
            return

        try:
            import openpyxl

            workbook = openpyxl.load_workbook(self.excel_file_path, data_only=True)
            sheet = workbook.active

            # Get header row
            headers = []
            for cell in sheet[1]:
                if cell.value:
                    headers.append(str(cell.value).strip())

            workbook.close()

            # Populate combo boxes
            for combo in self.column_combos.values():
                combo.clear()
                combo.addItem("-- Non mappato --", "")
                for header in headers:
                    combo.addItem(header, header)

            # Try to auto-match saved mappings
            self.apply_saved_mappings()

        except Exception as e:
            QMessageBox.warning(
                self,
                "Errore",
                f"Impossibile leggere le colonne dal file Excel:\n{str(e)}",
            )

    def validate_data(self):
        """Validate Excel data before import."""
        # Check reason length
        reason = self.reason_input.text().strip()
        if len(reason) < 10:
            QMessageBox.warning(
                self,
                "Errore",
                "Il motivo deve contenere almeno 10 caratteri.",
            )
            return

        # Get column mapping
        column_mapping = {}
        for field_id, combo in self.column_combos.items():
            excel_col = combo.currentData()
            if excel_col:
                column_mapping[field_id] = excel_col

        # Check required fields
        required_fields = [
            "owner_name",
            "license_plate",
            "subscription_start",
            "payment_details",
        ]

        missing_fields = [f for f in required_fields if f not in column_mapping]
        if missing_fields:
            QMessageBox.warning(
                self,
                "Errore",
                f"Campi obbligatori non mappati:\n{', '.join(missing_fields)}",
            )
            return

        # Save column mappings for future use
        self.save_column_mappings(column_mapping)

        # Read Excel file
        self.progress_label.setText("Lettura file Excel...")
        self.progress_bar.setValue(0)

        success, error_msg, data_rows = read_excel_file(
            self.excel_file_path, column_mapping
        )

        if not success:
            QMessageBox.critical(
                self, "Errore", f"Errore nella lettura del file:\n{error_msg}"
            )
            self.progress_bar.setValue(0)
            self.progress_label.setText("Pronto per l'importazione")
            return

        self.excel_data = data_rows
        total_rows = len(data_rows)
        total_steps = total_rows * 2  # validation + import on one bar

        self.progress_bar.setMaximum(total_steps)
        self.progress_label.setText(f"Validazione {total_rows} righe...")
        self.progress_bar.setValue(0)

        # Validate all rows
        def validation_progress(current, total):
            self.progress_bar.setValue(current)
            self.progress_label.setText(f"Validazione: {current}/{total_rows} righe...")

        is_valid, errors, validated_rows = validate_all_rows(
            data_rows, self.db_manager, validation_progress
        )

        if is_valid:
            self.validated_data = validated_rows
            self.progress_label.setText(
                f"✓ Validazione completata: {len(validated_rows)} righe valide"
            )
            self.progress_bar.setValue(total_rows)  # halfway (validation done)
            self.import_button.setEnabled(True)

            QMessageBox.information(
                self,
                "Validazione Completata",
                f"Tutti i dati sono validi!\n\n"
                f"Righe da importare: {len(validated_rows)}\n\n"
                f"Clicca 'Importa' per procedere con l'inserimento nel database.",
            )
        else:
            self.progress_label.setText(f"✗ Errori di validazione: {len(errors)}")
            self.progress_bar.setValue(0)
            self.import_button.setEnabled(False)

            # Show error dialog
            self.show_validation_errors(errors)

    def show_validation_errors(self, errors: list[tuple[int, str, str]]):
        """Show validation errors in a dialog."""
        error_dialog = QDialog(self)
        error_dialog.setWindowTitle("Errori di Validazione")
        error_dialog.setMinimumWidth(700)
        error_dialog.setMinimumHeight(500)

        layout = QVBoxLayout()

        # Info label
        info_label = QLabel(
            f"Trovati {len(errors)} errori. "
            f"Correggi il file Excel e riprova la validazione."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Error text area
        error_text = QTextEdit()
        error_text.setReadOnly(True)

        # Format errors in row order
        error_lines = []
        for row_num, field, error_msg in sorted(errors, key=lambda x: x[0]):
            error_lines.append(f"Riga {row_num}, Campo '{field}': {error_msg}")

        error_text.setPlainText("\n".join(error_lines))
        layout.addWidget(error_text)

        # Buttons
        button_layout = QHBoxLayout()

        copy_button = QPushButton("Copia negli Appunti")
        copy_button.clicked.connect(
            lambda: self.copy_to_clipboard("\n".join(error_lines))
        )
        button_layout.addWidget(copy_button)

        button_layout.addStretch()

        close_button = QPushButton("Chiudi")
        close_button.clicked.connect(error_dialog.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        error_dialog.setLayout(layout)
        error_dialog.exec()

    def copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        QMessageBox.information(self, "Copiato", "Errori copiati negli appunti!")

    def import_data(self):
        """Import validated data into database."""
        if not self.validated_data:
            QMessageBox.warning(self, "Errore", "Nessun dato validato da importare.")
            return

        reason = self.reason_input.text().strip()
        total = len(self.validated_data)

        # Confirm import
        reply = QMessageBox.question(
            self,
            "Conferma Importazione",
            f"Confermi l'importazione di {total} abbonamenti?\n\n"
            f"Questa operazione non può essere annullata.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Disable buttons during import
        self.validate_button.setEnabled(False)
        self.import_button.setEnabled(False)
        self.browse_button.setEnabled(False)

        total_rows = len(self.validated_data)
        total_steps = total_rows * 2

        self.progress_label.setText("Importazione in corso...")
        self.progress_bar.setMaximum(total_steps)
        self.progress_bar.setValue(total_rows)  # continue from validation progress

        # Progress callback
        def import_progress(current, total_count):
            progress_value = total_rows + current
            self.progress_bar.setValue(progress_value)
            self.progress_label.setText(
                f"Importazione: {current}/{total_count} abbonamenti..."
            )

        # Perform bulk import
        success, error_msg = self.db_manager.bulk_add_subscriptions(
            self.validated_data, reason, import_progress
        )

        if success:
            self.progress_bar.setValue(total_steps)
            self.progress_label.setText(
                f"✓ Importazione completata: {total} abbonamenti inseriti"
            )

            QMessageBox.information(
                self,
                "Importazione Completata",
                f"Importati con successo {total} abbonamenti nel database!",
            )

            self.import_completed.emit(total)
            self.accept()
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText("✗ Errore durante l'importazione")

            QMessageBox.critical(
                self,
                "Errore Importazione",
                f"Si è verificato un errore durante l'importazione:\n\n{error_msg}\n\n"
                f"Nessun dato è stato importato (transazione annullata).",
            )

            # Re-enable buttons
            self.validate_button.setEnabled(True)
            self.import_button.setEnabled(False)
            self.browse_button.setEnabled(True)

    def get_mappings_file_path(self) -> Path:
        """Get path to column mappings config file."""
        config_dir = get_app_data_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "import_mappings.json"

    def save_column_mappings(self, mappings: dict[str, str]):
        """Save column mappings to config file."""
        try:
            config_path = self.get_mappings_file_path()
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(mappings, f, ensure_ascii=False, indent=2)
        except Exception:
            # Silently fail - not critical
            pass

    def load_column_mappings(self):
        """Load saved column mappings from config file."""
        try:
            config_path = self.get_mappings_file_path()
            if not config_path.exists():
                return

            with open(config_path, "r", encoding="utf-8") as f:
                self.saved_mappings = json.load(f)
        except Exception:
            self.saved_mappings = {}

    def apply_saved_mappings(self):
        """Apply saved mappings to combo boxes if columns match."""
        if not hasattr(self, "saved_mappings"):
            return

        for field_id, excel_col in self.saved_mappings.items():
            if field_id in self.column_combos:
                combo = self.column_combos[field_id]
                # Find and select the matching column
                for i in range(combo.count()):
                    if combo.itemData(i) == excel_col:
                        combo.setCurrentIndex(i)
                        break
