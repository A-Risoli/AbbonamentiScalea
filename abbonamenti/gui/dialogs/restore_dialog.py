"""
Restore dialog for restoring encrypted database backups
"""
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QFormLayout,
)

from abbonamenti.database.manager import DatabaseManager
from abbonamenti.gui.styles import get_stylesheet
from abbonamenti.utils.paths import get_backups_dir


class RestoreThread(QThread):
    """Background thread for performing restore"""
    progress = pyqtSignal(int, int, str)  # step, total_steps, message
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, db_manager: DatabaseManager, backup_path: Path, passphrase: str):
        super().__init__()
        self.db_manager = db_manager
        self.backup_path = backup_path
        self.passphrase = passphrase
    
    def run(self):
        """Perform restore in background"""
        try:
            success, result = self.db_manager.restore_secure_backup(
                self.backup_path,
                self.passphrase,
                progress_callback=self.progress.emit
            )
            self.finished.emit(success, result)
        except Exception as e:
            self.finished.emit(False, str(e))


class RestoreDialog(QDialog):
    """Dialog for restoring encrypted backups"""
    
    restore_completed = pyqtSignal()
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.restore_thread = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Ripristina Backup Cifrato")
        self.setMinimumWidth(550)
        self.setMinimumHeight(350)
        self.setStyleSheet(get_stylesheet())
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Warning label
        warning_label = QLabel(
            "⚠️ ATTENZIONE: Il ripristino sostituirà il database e le chiavi correnti!\n"
            "Prima del ripristino verrà creato un backup automatico dei file attuali."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet(
            "color: #d32f2f; background: #ffebee; padding: 12px; "
            "border-radius: 4px; font-weight: bold;"
        )
        layout.addWidget(warning_label)
        
        # Backup file group
        file_group = QGroupBox("File Backup")
        file_layout = QHBoxLayout(file_group)
        
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Seleziona file .enc da ripristinare")
        self.file_input.setReadOnly(True)
        file_layout.addWidget(self.file_input)
        
        browse_btn = QPushButton("Sfoglia...")
        browse_btn.clicked.connect(self.browse_backup_file)
        file_layout.addWidget(browse_btn)
        
        layout.addWidget(file_group)
        
        # Passphrase group
        pass_group = QGroupBox("Passphrase Backup")
        pass_layout = QFormLayout(pass_group)
        pass_layout.setSpacing(12)
        
        info_label = QLabel("Inserisci la passphrase usata durante la creazione del backup")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        pass_layout.addRow("", info_label)
        
        self.passphrase_input = QLineEdit()
        self.passphrase_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_input.setPlaceholderText("Inserisci passphrase")
        self.passphrase_input.textChanged.connect(self.validate_inputs)
        pass_layout.addRow("Passphrase *:", self.passphrase_input)
        
        layout.addWidget(pass_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.progress_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Annulla")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.restore_btn = QPushButton("Ripristina Backup")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self.start_restore)
        self.restore_btn.setStyleSheet(
            "QPushButton { background: #f44336; color: white; font-weight: bold; "
            "padding: 8px 24px; } "
            "QPushButton:hover { background: #d32f2f; } "
            "QPushButton:disabled { background: #ccc; }"
        )
        button_layout.addWidget(self.restore_btn)
        
        layout.addLayout(button_layout)
    
    def browse_backup_file(self):
        """Open file browser for backup file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleziona File Backup",
            str(get_backups_dir()),
            "Backup Files (*.enc);;All Files (*)"
        )
        if file_path:
            self.file_input.setText(file_path)
            self.validate_inputs()
    
    def validate_inputs(self):
        """Validate file and passphrase"""
        has_file = bool(self.file_input.text())
        has_passphrase = bool(self.passphrase_input.text())
        
        self.restore_btn.setEnabled(has_file and has_passphrase)
    
    def start_restore(self):
        """Start restore process with confirmation"""
        # Final confirmation
        reply = QMessageBox.warning(
            self,
            "Conferma Ripristino",
            "Sei sicuro di voler ripristinare il backup?\n\n"
            "Il database e le chiavi correnti verranno sostituiti!\n"
            "Un backup automatico dei file correnti verrà creato prima del ripristino.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        backup_path = Path(self.file_input.text())
        passphrase = self.passphrase_input.text()
        
        # Disable inputs
        self.passphrase_input.setEnabled(False)
        self.file_input.setEnabled(False)
        self.restore_btn.setEnabled(False)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(5)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        
        # Start restore thread
        self.restore_thread = RestoreThread(self.db_manager, backup_path, passphrase)
        self.restore_thread.progress.connect(self.on_progress)
        self.restore_thread.finished.connect(self.on_finished)
        self.restore_thread.start()
    
    def on_progress(self, step: int, total: int, message: str):
        """Update progress"""
        self.progress_bar.setValue(step)
        self.progress_label.setText(message)
    
    def on_finished(self, success: bool, result: str):
        """Handle restore completion"""
        if success:
            QMessageBox.information(
                self,
                "Ripristino Completato",
                f"{result}\n\n"
                "I dati verranno ricaricati automaticamente."
            )
            self.restore_completed.emit()
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Errore Ripristino",
                f"Impossibile ripristinare il backup:\n\n{result}"
            )
            # Re-enable inputs
            self.passphrase_input.setEnabled(True)
            self.file_input.setEnabled(True)
            self.restore_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
