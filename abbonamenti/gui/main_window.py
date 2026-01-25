import sys
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QPalette
from PyQt6.QtWidgets import (
    QDialog,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QStyle,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from abbonamenti.database.manager import DatabaseManager
from abbonamenti.gui.dialogs.add_edit_dialog import (
    AddEditSubscriptionDialog,
    DeleteSubscriptionDialog,
)
from abbonamenti.gui.dialogs.audit_viewer import AuditLogViewer
from abbonamenti.gui.dialogs.backup_dialog import BackupDialog
from abbonamenti.gui.dialogs.import_dialog import ImportDialog
from abbonamenti.gui.dialogs.key_export_dialog import KeyExportDialog
from abbonamenti.gui.dialogs.key_import_dialog import KeyImportDialog
from abbonamenti.gui.dialogs.restore_dialog import RestoreDialog
from abbonamenti.gui.dialogs.statistics_viewer import StatisticsViewer
from abbonamenti.gui.models import SubscriptionsTableModel
from abbonamenti.gui.styles import get_stylesheet
from abbonamenti.utils.paths import get_database_path, get_keys_dir


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager(get_database_path(), get_keys_dir())
        self.edit_mode_enabled = False
        self.has_modifications = False  # Track if data was modified
        self.model = SubscriptionsTableModel(self.db_manager.get_all_subscriptions())
        self.init_ui()
        self.check_data_integrity()

    def init_ui(self):
        self.setWindowTitle("AbbonaMunicipale - Sistema Abbonamenti Città di Scalea")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

        # Set window icon if available
        from pathlib import Path
        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Apply modern stylesheet
        self.setStyleSheet(get_stylesheet())

        self.create_menubar()
        self.create_toolbar()
        self.create_central_widget()
        self.create_status_bar()

    def create_menubar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        export_action = QAction("Esporta CSV", self)
        export_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)

        self.import_action = QAction("Importa Excel", self)
        self.import_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.import_action.triggered.connect(self.import_from_excel)
        file_menu.addAction(self.import_action)

        file_menu.addSeparator()

        exit_action = QAction("Esci", self)
        exit_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = menubar.addMenu("&Strumenti")

        backup_action = QAction("Backup Database", self)
        backup_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DriveHDIcon))
        backup_action.triggered.connect(self.backup_database)
        tools_menu.addAction(backup_action)

        restore_action = QAction("Ripristina Backup", self)
        restore_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        restore_action.triggered.connect(self.restore_database)
        tools_menu.addAction(restore_action)

        tools_menu.addSeparator()

        key_export_action = QAction("🔑 Esporta Chiave di Recupero", self)
        key_export_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        key_export_action.triggered.connect(self.export_recovery_keys)
        key_export_action.setToolTip(
            "CRITICO: Esporta le chiavi di cifratura per recuperare i backup"
        )
        tools_menu.addAction(key_export_action)

        key_import_action = QAction("Ripristina Chiavi di Recupero", self)
        key_import_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        key_import_action.triggered.connect(self.import_recovery_keys)
        key_import_action.setToolTip(
            "Usa il file chiavi .enc/.zip per poter aprire i backup cifrati"
        )
        tools_menu.addAction(key_import_action)

        tools_menu.addSeparator()

        audit_action = QAction("Visualizza Log Audit", self)
        audit_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        audit_action.triggered.connect(self.show_audit_log)
        tools_menu.addAction(audit_action)

        help_menu = menubar.addMenu("&Aiuto")

        about_action = QAction("Informazioni", self)
        about_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.integrity_label = QLabel("Integrità Dati: ")
        label_color = toolbar.palette().color(QPalette.ColorRole.WindowText).name()
        self.integrity_label.setStyleSheet(f"color: {label_color}; background: transparent;")
        toolbar.addWidget(self.integrity_label)

        self.integrity_indicator = QLabel("✓")
        self.integrity_indicator.setStyleSheet(
            "color: green; font-weight: bold; font-size: 14px; padding: 0px 8px;"
            "background: transparent;"
        )
        self.integrity_indicator.setToolTip("Tutti i dati sono validi e sicuri")
        toolbar.addWidget(self.integrity_indicator)

        toolbar.addSeparator()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cerca per proprietario, targa o protocollo...")
        self.search_input.setMinimumWidth(250)
        self.search_input.setMaximumWidth(350)
        self.search_input.textChanged.connect(lambda text: self.on_search(text))
        toolbar.addWidget(self.search_input)

        toolbar.addSeparator()

        self.edit_mode_action = QPushButton("🔓 Modalità Modifica: OFF")
        self.edit_mode_action.setCheckable(True)
        self.edit_mode_action.setMinimumHeight(32)
        self.edit_mode_action.toggled.connect(self.toggle_edit_mode)
        toolbar.addWidget(self.edit_mode_action)

        # Add spacing widget
        spacer = QWidget()
        spacer.setMinimumWidth(10)
        toolbar.addWidget(spacer)

        self.add_btn = QPushButton("➕ Aggiungi")
        self.add_btn.setEnabled(False)
        self.add_btn.setMinimumHeight(32)
        self.add_btn.setMinimumWidth(100)
        self.add_btn.clicked.connect(self.add_subscription)
        toolbar.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️  Modifica")
        self.edit_btn.setEnabled(False)
        self.edit_btn.setMinimumHeight(32)
        self.edit_btn.setMinimumWidth(100)
        self.edit_btn.clicked.connect(self.edit_subscription)
        toolbar.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️  Elimina")
        self.delete_btn.setEnabled(False)
        self.delete_btn.setMinimumHeight(32)
        self.delete_btn.setMinimumWidth(100)
        self.delete_btn.setObjectName("deleteBtn")
        self.delete_btn.clicked.connect(self.delete_subscription)
        toolbar.addWidget(self.delete_btn)

        # Add stretch spacer
        stretch_spacer = QWidget()
        stretch_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        toolbar.addWidget(stretch_spacer)

        # Statistics button
        stats_btn = QPushButton("📊 Statistiche")
        stats_btn.setMinimumHeight(38)
        stats_btn.setMinimumWidth(140)
        stats_btn.setStyleSheet("font-weight: bold; font-size: 13px;")
        stats_btn.setToolTip("Visualizza statistiche pagamenti")
        stats_btn.clicked.connect(self.show_statistics)
        toolbar.addWidget(stats_btn)

    def create_central_widget(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setColumnHidden(9, False)
        self.table_view.setShowGrid(True)
        self.table_view.setGridStyle(Qt.PenStyle.SolidLine)
        self.table_view.setSortingEnabled(True)
        
        # Make header responsive with stretch
        horizontal_header = self.table_view.horizontalHeader()
        horizontal_header.setStretchLastSection(False)
        horizontal_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Protocol ID
        horizontal_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Owner Name
        horizontal_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Plate
        horizontal_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Email
        horizontal_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Address
        horizontal_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Mobile
        horizontal_header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Start Date
        horizontal_header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # End Date
        horizontal_header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # Payment Method
        horizontal_header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # Status

        # Enable sorting
        self.table_view.setSortingEnabled(True)
        
        # Set default sort order: Protocol ID descending (newest first)
        self.table_view.sortByColumn(0, Qt.SortOrder.DescendingOrder)

        # Set row height for better visibility
        self.table_view.verticalHeader().setDefaultSectionSize(28)
        self.table_view.setRowHeight(0, 28)

        layout.addWidget(self.table_view)

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()

    def toggle_edit_mode(self, checked: bool):
        self.edit_mode_enabled = checked

        if checked:
            self.edit_mode_action.setText("🔓 Modalità Modifica: ON")
            self.add_btn.setEnabled(True)
            self.edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            self.import_action.setEnabled(True)
            self.status_bar.showMessage(
                "✓ Modalità Modifica Attiva - Tutte le modifiche verranno registrate"
            )
        else:
            self.edit_mode_action.setText("🔓 Modalità Modifica: OFF")
            self.add_btn.setEnabled(False)
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.import_action.setEnabled(False)
            self.status_bar.showMessage("Modalità sola lettura")

    @pyqtSlot()
    def on_search(self, text: str):
        if text:
            subscriptions = self.db_manager.search_subscriptions(text)
        else:
            subscriptions = self.db_manager.get_all_subscriptions()
        self.model.update_data(subscriptions)

    def check_data_integrity(self):
        is_valid, issues = self.db_manager.verify_data_integrity()

        if is_valid:
            self.integrity_indicator.setText("✓")
            self.integrity_indicator.setStyleSheet(
                "color: green; font-weight: bold; font-size: 16px; background: transparent;"
            )
            self.integrity_indicator.setToolTip("Tutti i dati sono validi e sicuri")
        else:
            self.integrity_indicator.setText("✗")
            self.integrity_indicator.setStyleSheet(
                "color: red; font-weight: bold; font-size: 16px; background: transparent;"
            )
            tooltip_text = "Problemi di integrità rilevati:\n" + "\n".join(issues)
            self.integrity_indicator.setToolTip(tooltip_text)
            QMessageBox.warning(
                self,
                "Problemi di Integrità Dati",
                f"Rilevati problemi di integrità:\n\n{tooltip_text}",
            )

    def update_status_bar(self):
        subscriptions = self.db_manager.get_all_subscriptions()
        today = datetime.now().date()

        active = 0
        expiring = 0
        expired = 0

        for sub in subscriptions:
            end_date = sub.subscription_end.date()
            if end_date < today:
                expired += 1
            elif (end_date - today).days <= 30:
                expiring += 1
            else:
                active += 1

        self.status_bar.showMessage(
            f"✓ Attivi: {active} | ⚠ In scadenza: {expiring} | "
            f"✗ Scaduti: {expired} | Totale: {len(subscriptions)}"
        )

    def load_data(self):
        """Reload subscriptions into the table and refresh status/integrity."""
        subscriptions = self.db_manager.get_all_subscriptions()
        self.model.update_data(subscriptions)
        self.update_status_bar()
        self.check_data_integrity()

    @pyqtSlot()
    def add_subscription(self):
        dialog = AddEditSubscriptionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                protocol_id = self.db_manager.add_subscription(
                    owner_name=data["owner_name"],
                    license_plate=data["license_plate"],
                    email=data["email"],
                    address=data["address"],
                    mobile=data["mobile"],
                    subscription_start=data["subscription_start"],
                    subscription_end=data["subscription_end"],
                    payment_details=data["payment_details"],
                    payment_method=data["payment_method"],
                    reason=data["reason"],
                )
                QMessageBox.information(
                    self,
                    "Successo",
                    f"Abbonamento aggiunto con successo!\n\n"
                    f"ID Protocollo: {protocol_id}",
                )
                self.model.update_data(self.db_manager.get_all_subscriptions())
                self.update_status_bar()
                self.has_modifications = True
            except Exception as e:
                QMessageBox.critical(
                    self, "Errore", f"Errore durante l'aggiunta: {str(e)}"
                )

    @pyqtSlot()
    def edit_subscription(self):
        selection_model = self.table_view.selectionModel()
        if not selection_model.hasSelection():
            QMessageBox.warning(
                self, "Attenzione", "Seleziona un abbonamento da modificare."
            )
            return

        selected_indexes = selection_model.selectedIndexes()
        if not selected_indexes:
            return

        selected_row = selected_indexes[0].row()
        protocol_id = str(
            self.model.data(
                self.model.index(selected_row, 0), Qt.ItemDataRole.DisplayRole
            )
        )
        subscription = self.db_manager.get_subscription(protocol_id)

        if not subscription:
            QMessageBox.warning(self, "Errore", "Abbonamento non trovato.")
            return

        dialog = AddEditSubscriptionDialog(self, subscription)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                success = self.db_manager.update_subscription(
                    protocol_id=protocol_id,
                    owner_name=data["owner_name"],
                    license_plate=data["license_plate"],
                    email=data["email"],
                    address=data["address"],
                    mobile=data["mobile"],
                    subscription_start=data["subscription_start"],
                    subscription_end=data["subscription_end"],
                    payment_details=data["payment_details"],
                    payment_method=data["payment_method"],
                    reason=data["reason"],
                )
                if success:
                    QMessageBox.information(
                        self,
                        "Successo",
                        "Abbonamento modificato con successo!",
                    )
                    self.model.update_data(self.db_manager.get_all_subscriptions())
                    self.update_status_bar()
                    self.has_modifications = True
                else:
                    QMessageBox.warning(
                        self, "Errore", "Impossibile modificare l'abbonamento."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "Errore", f"Errore durante la modifica: {str(e)}"
                )

    @pyqtSlot()
    def delete_subscription(self):
        from PyQt6.QtWidgets import QDialog

        selection_model = self.table_view.selectionModel()
        if not selection_model.hasSelection():
            QMessageBox.warning(
                self, "Attenzione", "Seleziona un abbonamento da eliminare."
            )
            return

        selected_indexes = selection_model.selectedIndexes()
        if not selected_indexes:
            return

        selected_row = selected_indexes[0].row()
        protocol_id = str(
            self.model.data(
                self.model.index(selected_row, 0), Qt.ItemDataRole.DisplayRole
            )
        )
        subscription = self.db_manager.get_subscription(protocol_id)

        if not subscription:
            QMessageBox.warning(self, "Errore", "Abbonamento non trovato.")
            return

        dialog = DeleteSubscriptionDialog(self, subscription)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            reason = dialog.get_reason()
            try:
                success = self.db_manager.delete_subscription(protocol_id, reason)
                if success:
                    QMessageBox.information(
                        self,
                        "Successo",
                        "Abbonamento eliminato con successo!",
                    )
                    self.model.update_data(self.db_manager.get_all_subscriptions())
                    self.update_status_bar()
                    self.has_modifications = True
                else:
                    QMessageBox.warning(
                        self, "Errore", "Impossibile eliminare l'abbonamento."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "Errore", f"Errore durante l'eliminazione: {str(e)}"
                )

    @pyqtSlot()
    def show_audit_log(self):
        viewer = AuditLogViewer(self)
        viewer.exec()

    @pyqtSlot()
    def show_statistics(self):
        """Show payment statistics dialog"""
        viewer = StatisticsViewer(self.db_manager, self)
        viewer.exec()

    @pyqtSlot()
    def export_data(self):
        import csv
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Esporta Abbonamenti", "", "File CSV (*.csv)"
        )

        if not file_path:
            return

        try:
            subscriptions = self.db_manager.get_all_subscriptions()
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "ID Protocollo",
                        "Nome Proprietario",
                        "Targa",
                        "Email",
                        "Indirizzo",
                        "Cellulare",
                        "Data Inizio",
                        "Data Fine",
                        "Metodo Pagamento",
                        "Data Creazione",
                        "Ultima Modifica",
                    ]
                )

                for sub in subscriptions:
                    writer.writerow(
                        [
                            sub.protocol_id,
                            sub.owner_name,
                            sub.license_plate,
                            sub.email if sub.email else "",
                            sub.address if sub.address else "",
                            sub.mobile if sub.mobile else "",
                            sub.subscription_start.strftime("%d/%m/%Y"),
                            sub.subscription_end.strftime("%d/%m/%Y"),
                            sub.payment_method,
                            sub.created_at.strftime("%d/%m/%Y %H:%M:%S")
                            if sub.created_at
                            else "",
                            sub.updated_at.strftime("%d/%m/%Y %H:%M:%S")
                            if sub.updated_at
                            else "",
                        ]
                    )

            QMessageBox.information(
                self, "Successo", "Abbonamenti esportati con successo!"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Errore", f"Errore durante l'esportazione: {str(e)}"
            )

    @pyqtSlot()
    def import_from_excel(self):
        """Open import dialog for bulk Excel import."""
        if not self.edit_mode_enabled:
            QMessageBox.warning(
                self,
                "Modalità Modifica Richiesta",
                "Per importare abbonamenti è necessario attivare la Modalità Modifica.\n\n"
                "Clicca sul pulsante '🔓 Modalità Modifica: OFF' nella toolbar per attivarla.",
            )
            return
        
        dialog = ImportDialog(self.db_manager, self)
        dialog.import_completed.connect(self.on_import_completed)
        dialog.exec()

    @pyqtSlot(int)
    def on_import_completed(self, count: int):
        """Handle successful import completion."""
        # Reload data to show new records
        self.load_data()
        
        # Update status bar
        self.status_bar.showMessage(
            f"✓ Importati {count} abbonamenti con successo", 5000
        )
        
        # Re-check integrity
        self.check_data_integrity()
        
        # Mark modifications
        self.has_modifications = True

    @pyqtSlot()
    def backup_database(self):
        """Open backup dialog to create encrypted backup"""
        dialog = BackupDialog(self.db_manager, self)
        dialog.backup_completed.connect(self.on_backup_completed)
        dialog.exec()
    
    @pyqtSlot(str)
    def on_backup_completed(self, backup_path: str):
        """Handle successful backup completion"""
        from pathlib import Path
        import os
        
        self.status_bar.showMessage(
            f"✓ Backup creato: {Path(backup_path).name}", 5000
        )
        
        # Ask if user wants to open folder
        reply = QMessageBox.question(
            self,
            "Backup Completato",
            f"Backup salvato in:\n{backup_path}\n\nVuoi aprire la cartella?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            os.startfile(str(Path(backup_path).parent))

    @pyqtSlot()
    def restore_database(self):
        """Open restore dialog to restore encrypted backup"""
        dialog = RestoreDialog(self.db_manager, self)
        dialog.restore_completed.connect(self.on_restore_completed)
        dialog.exec()
    
    @pyqtSlot()
    def on_restore_completed(self):
        """Handle successful restore completion - reload data"""
        # Reload all data from restored database
        self.load_data()
        
        # Re-check integrity
        self.check_data_integrity()
        
        # Show success message
        QMessageBox.information(
            self,
            "Ripristino Completato",
            "Il database è stato ripristinato con successo!\n\n"
            "I dati sono stati ricaricati automaticamente."
        )
        
        self.status_bar.showMessage("✓ Database ripristinato con successo", 5000)

    @pyqtSlot()
    def export_recovery_keys(self):
        """Open key export dialog"""
        from abbonamenti.utils.paths import get_keys_dir
        
        # Show critical warning first
        reply = QMessageBox.warning(
            self,
            "⚠️ CHIAVI DI RECUPERO",
            "Stai per esportare le CHIAVI DI CIFRATURA del database.\n\n"
            "🔴 ATTENZIONE CRITICA:\n"
            "Senza queste chiavi, TUTTI i backup del database sono INUTILI!\n"
            "Se le chiavi vengono perse, i dati cifrati non potranno MAI\n"
            "essere recuperati (nomi, targhe, indirizzi, email, telefoni).\n\n"
            "📌 OBBLIGATORIO:\n"
            "• Salva le chiavi su chiavetta USB separata\n"
            "• Conservale in cassaforte\n"
            "• Crea copie multiple in luoghi sicuri diversi\n\n"
            "Vuoi procedere con l'esportazione?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            dialog = KeyExportDialog(get_keys_dir(), self)
            dialog.exec()

    @pyqtSlot()
    def import_recovery_keys(self):
        """Restore key backup (.enc or .zip) without terminal commands"""
        from abbonamenti.utils.paths import get_keys_dir

        dialog = KeyImportDialog(get_keys_dir(), self)
        dialog.exec()

    @pyqtSlot()
    def show_about(self):
        QMessageBox.about(
            self,
            "Informazioni",
            "AbbonaMunicipale\n"
            "\n\nRisoli Antonio\n\n"
            "Sistema Abbonamenti Città di Scalea\n\n"
            "Sicuro, affidabile, facile da usare.\n\n"
            "Versione 0.1.2",
        )

    def closeEvent(self, event):
        """Handle application close - perform silent backup if modifications exist."""
        if self.has_modifications:
            try:
                # Silent backup with auto-generated passphrase from HMAC key
                from datetime import datetime
                from abbonamenti.utils.paths import get_backups_dir
                import hashlib
                
                # Derive passphrase from HMAC key (always available)
                hmac_key_path = get_keys_dir() / "hmac_key.bin"
                with open(hmac_key_path, "rb") as f:
                    hmac_key = f.read()
                # Create a deterministic 32-char passphrase from HMAC key
                passphrase = hashlib.sha256(hmac_key + b"auto_backup_salt").hexdigest()[:32]
                
                backup_filename = f"auto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.enc"
                backup_path = get_backups_dir() / backup_filename
                
                # Perform silent backup
                self.db_manager.perform_secure_backup(
                    str(backup_path),
                    passphrase,
                    progress_callback=None  # Silent mode
                )
            except Exception:
                # Silently fail - don't block app close
                pass
        
        event.accept()


def main():
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
