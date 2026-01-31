"""
Backup dialog for creating encrypted database backups
"""
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
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


class BackupThread(QThread):
    """Background thread for performing backup"""
    progress = pyqtSignal(int, int, str)  # step, total_steps, message
    finished = pyqtSignal(bool, str)  # success, message_or_path
    
    def __init__(self, db_manager: DatabaseManager, output_dir: Path, passphrase: str):
        super().__init__()
        self.db_manager = db_manager
        self.output_dir = output_dir
        self.passphrase = passphrase
    
    def run(self):
        """Perform backup in background"""
        try:
            success, result = self.db_manager.perform_secure_backup(
                self.output_dir,
                self.passphrase,
                progress_callback=self.progress.emit
            )
            self.finished.emit(success, result)
        except Exception as e:
            self.finished.emit(False, str(e))


class BackupDialog(QDialog):
    """Dialog for creating encrypted backups"""
    
    backup_completed = pyqtSignal(str)  # backup_path
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.backup_thread = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Backup Database Cifrato")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        self.setStyleSheet(get_stylesheet())
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Info label
        info_label = QLabel(
            "Crea un backup cifrato del database e delle chiavi di cifratura.\n"
            "Il backup sarà protetto da una passphrase sicura."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 8px;")
        layout.addWidget(info_label)
        
        # Destination group
        dest_group = QGroupBox("Destinazione Backup")
        dest_layout = QHBoxLayout(dest_group)
        
        self.dest_input = QLineEdit()
        self.dest_input.setText(str(get_backups_dir()))
        self.dest_input.setReadOnly(True)
        dest_layout.addWidget(self.dest_input)
        
        browse_btn = QPushButton("Sfoglia...")
        browse_btn.clicked.connect(self.browse_destination)
        dest_layout.addWidget(browse_btn)
        
        layout.addWidget(dest_group)
        
        # Passphrase group
        pass_group = QGroupBox("Passphrase Cifratura")
        pass_layout = QFormLayout(pass_group)
        pass_layout.setSpacing(12)
        
        self.passphrase_input = QLineEdit()
        self.passphrase_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_input.setPlaceholderText("Minimo 16 caratteri")
        self.passphrase_input.textChanged.connect(self.validate_passphrase)
        pass_layout.addRow("Passphrase *:", self.passphrase_input)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("Conferma passphrase")
        self.confirm_input.textChanged.connect(self.validate_passphrase)
        pass_layout.addRow("Conferma *:", self.confirm_input)
        
        self.strength_label = QLabel("")
        self.strength_label.setStyleSheet("color: #999; font-size: 11px;")
        pass_layout.addRow("", self.strength_label)
        
        warning_label = QLabel(
            "⚠️ IMPORTANTE: Salva questa passphrase in un luogo sicuro!\n"
            "Senza la passphrase non potrai ripristinare il backup."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet(
            "color: #ff6b00; background: #fff3e0; padding: 8px; "
            "border-radius: 4px; font-size: 11px;"
        )
        pass_layout.addRow("", warning_label)
        
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
        
        self.backup_btn = QPushButton("Crea Backup")
        self.backup_btn.setEnabled(False)
        self.backup_btn.clicked.connect(self.start_backup)
        self.backup_btn.setStyleSheet(
            "QPushButton { background: #2196F3; color: white; font-weight: bold; "
            "padding: 8px 24px; } "
            "QPushButton:hover { background: #1976D2; } "
            "QPushButton:disabled { background: #ccc; }"
        )
        button_layout.addWidget(self.backup_btn)
        
        layout.addLayout(button_layout)
    
    def browse_destination(self):
        """Open folder browser"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleziona Cartella Backup",
            self.dest_input.text()
        )
        if folder:
            self.dest_input.setText(folder)
    
    def validate_passphrase(self):
        """Validate passphrase and show strength"""
        passphrase = self.passphrase_input.text()
        confirm = self.confirm_input.text()
        
        # Check length
        if len(passphrase) < 16:
            self.strength_label.setText(f"Troppo corta ({len(passphrase)}/16 caratteri)")
            self.strength_label.setStyleSheet("color: #f44336; font-size: 11px;")
            self.backup_btn.setEnabled(False)
            return
        
        # Check match
        if passphrase != confirm:
            self.strength_label.setText("Le passphrase non coincidono")
            self.strength_label.setStyleSheet("color: #ff9800; font-size: 11px;")
            self.backup_btn.setEnabled(False)
            return
        
        # Check strength
        strength = 0
        if any(c.islower() for c in passphrase):
            strength += 1
        if any(c.isupper() for c in passphrase):
            strength += 1
        if any(c.isdigit() for c in passphrase):
            strength += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in passphrase):
            strength += 1
        
        if strength <= 1:
            self.strength_label.setText("✓ Valida (Debole - aggiungi numeri/simboli)")
            self.strength_label.setStyleSheet("color: #ff9800; font-size: 11px;")
        elif strength <= 2:
            self.strength_label.setText("✓ Valida (Media)")
            self.strength_label.setStyleSheet("color: #2196F3; font-size: 11px;")
        else:
            self.strength_label.setText("✓ Valida (Forte)")
            self.strength_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        
        self.backup_btn.setEnabled(True)
    
    def start_backup(self):
        """Start backup process"""
        output_dir = Path(self.dest_input.text())
        passphrase = self.passphrase_input.text()
        
        # Disable inputs
        self.passphrase_input.setEnabled(False)
        self.confirm_input.setEnabled(False)
        self.dest_input.setEnabled(False)
        self.backup_btn.setEnabled(False)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(6)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        
        # Start backup thread
        self.backup_thread = BackupThread(self.db_manager, output_dir, passphrase)
        self.backup_thread.progress.connect(self.on_progress)
        self.backup_thread.finished.connect(self.on_finished)
        self.backup_thread.start()
    
    def on_progress(self, step: int, total: int, message: str):
        """Update progress"""
        self.progress_bar.setValue(step)
        self.progress_label.setText(message)
    
    def on_finished(self, success: bool, result: str):
        """Handle backup completion - generate and show recovery sheet"""
        if success:
            # Store for recovery sheet generation
            self.last_backup_path = result
            self.last_passphrase = self.passphrase_input.text()
            
            QMessageBox.information(
                self,
                "Backup Completato",
                f"Backup creato con successo:\n\n{result}"
            )
            
            # Generate recovery sheet automatically
            self.generate_recovery_sheet()
        else:
            QMessageBox.critical(
                self,
                "Errore Backup",
                f"Impossibile creare il backup:\n\n{result}"
            )
            # Re-enable inputs
            self.passphrase_input.setEnabled(True)
            self.confirm_input.setEnabled(True)
            self.dest_input.setEnabled(True)
            self.backup_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
    
    def generate_recovery_sheet(self):
        """Generate and automatically open emergency recovery sheet PDF"""
        from abbonamenti.utils.recovery_sheet import generate_recovery_sheet_pdf
        from abbonamenti.utils.paths import get_backups_dir
        from datetime import datetime
        import os
        
        try:
            # Prepare recovery sheet path
            recovery_dir = get_backups_dir().parent / "recovery_sheets"
            recovery_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            recovery_path = recovery_dir / f"recovery_sheet_{timestamp}.pdf"
            
            # Generate PDF
            backup_location = (
                f"Backup: {self.last_backup_path}\n\n"
                "Conservare su chiavetta USB in cassaforte."
            )
            
            success = generate_recovery_sheet_pdf(
                password=self.last_passphrase,
                backup_location=backup_location,
                output_path=recovery_path,
                sheet_type="backup"
            )
            
            if success:
                # Open PDF in default viewer automatically
                os.startfile(str(recovery_path))
                
                # Ask if user wants to open backup folder
                reply = QMessageBox.question(
                    self,
                    "Scheda Generata",
                    "La scheda di recupero è stata generata e aperta.\n\n"
                    "Vuoi aprire la cartella dei backup?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    os.startfile(str(Path(self.last_backup_path).parent))
                
                self.backup_completed.emit(self.last_backup_path)
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Errore",
                    "Impossibile generare la scheda di recupero."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Errore",
                f"Errore generazione scheda:\n\n{str(e)}"
            )
