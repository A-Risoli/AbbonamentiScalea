"""
Master Key Export dialog for backing up encryption keys
"""
from pathlib import Path
import zipfile
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QCheckBox,
)

from abbonamenti.gui.styles import get_stylesheet
from abbonamenti.security.crypto import derive_key_from_passphrase, encrypt_with_key


class KeyExportDialog(QDialog):
    """Dialog for exporting master encryption keys"""
    
    def __init__(self, keys_dir: Path, parent=None):
        super().__init__(parent)
        self.keys_dir = keys_dir
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Esporta Chiave di Recupero")
        self.setMinimumWidth(520)
        self.setMinimumHeight(450)
        self.setStyleSheet(get_stylesheet())
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Critical warning
        warning_label = QLabel(
            "🔑 CHIAVI DI RECUPERO - LEGGERE ATTENTAMENTE\n\n"
            "⚠️ ATTENZIONE CRITICA:\n"
            "Senza queste chiavi, TUTTI i backup del database sono INUTILI!\n"
            "Se il computer si guasta e le chiavi vengono perse, non potrai MAI più\n"
            "recuperare i dati cifrati (nomi, targhe, indirizzi, email, telefoni).\n\n"
            "📌 OBBLIGATORIO:\n"
            "• Salva questo file su una chiavetta USB separata\n"
            "• Conservalo in un luogo sicuro (cassaforte)\n"
            "• NON salvarlo sullo stesso computer del database\n"
            "• Crea più copie e conservale in luoghi diversi"
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet(
            "color: #ffffff; background: #c62828; padding: 16px; "
            "border-radius: 6px; font-weight: bold; font-size: 12px;"
        )
        layout.addWidget(warning_label)
        
        # Protection password (MANDATORY)
        protection_group = QGroupBox("Protezione Chiavi (Obbligatoria)")
        protection_layout = QFormLayout(protection_group)
        protection_layout.setSpacing(12)
        
        info_label = QLabel(
            "Le chiavi verranno esportate in un archivio ZIP cifrato.\n"
            "Proteggi con una password sicura (minimo 16 caratteri)."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 8px;")
        protection_layout.addRow(info_label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Minimo 16 caratteri")
        self.password_input.textChanged.connect(self.validate_passphrase)
        protection_layout.addRow("Password *:", self.password_input)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("Conferma password")
        self.confirm_input.textChanged.connect(self.validate_passphrase)
        protection_layout.addRow("Conferma *:", self.confirm_input)
        
        self.strength_label = QLabel("")
        self.strength_label.setStyleSheet("color: #999; font-size: 11px;")
        protection_layout.addRow("", self.strength_label)
        
        warning_label2 = QLabel(
            "⚠️ IMPORTANTE: Salva questa password in un luogo sicuro!\n"
            "Senza la password non potrai recuperare queste chiavi."
        )
        warning_label2.setWordWrap(True)
        warning_label2.setStyleSheet(
            "color: #ff6b00; background: #fff3e0; padding: 8px; "
            "border-radius: 4px; font-size: 11px;"
        )
        protection_layout.addRow("", warning_label2)
        
        layout.addWidget(protection_group)
        
        # Instructions
        instructions_label = QLabel(
            "📝 DOPO L'ESPORTAZIONE:\n"
            "1. Salva il file su almeno 2 chiavette USB diverse\n"
            "2. Etichetta le chiavette: \"CHIAVI RECUPERO ABBONAMENTI - CRITICO\"\n"
            "3. Conserva una copia in cassaforte\n"
            "4. Annota la password in un luogo sicuro separato\n"
            "5. NON inviare via email o cloud"
        )
        instructions_label.setWordWrap(True)
        instructions_label.setStyleSheet(
            "color: #1565c0; background: #e3f2fd; padding: 12px; "
            "border-radius: 4px; font-size: 11px;"
        )
        layout.addWidget(instructions_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.export_btn = QPushButton("🔑 Esporta Chiavi")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_keys)
        self.export_btn.setStyleSheet(
            "QPushButton { background: #c62828; color: white; font-weight: bold; "
            "padding: 10px 24px; font-size: 13px; } "
            "QPushButton:hover { background: #b71c1c; }"
            "QPushButton:disabled { background: #999; }"
        )
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
    
    def validate_passphrase(self):
        """Validate passphrase and enable export button"""
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        
        if not password or not confirm:
            self.strength_label.setText("")
            self.export_btn.setEnabled(False)
            return
        
        if len(password) < 16:
            self.strength_label.setText("✗ Troppo corta (minimo 16 caratteri)")
            self.strength_label.setStyleSheet("color: #d32f2f; font-size: 11px;")
            self.export_btn.setEnabled(False)
            return
        
        if password != confirm:
            self.strength_label.setText("✗ Le password non coincidono")
            self.strength_label.setStyleSheet("color: #d32f2f; font-size: 11px;")
            self.export_btn.setEnabled(False)
            return
        
        # Calculate strength
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password)
        
        strength = sum([has_lower, has_upper, has_digit, has_symbol])
        
        if strength <= 1:
            self.strength_label.setText("✓ Valida (Debole - aggiungi numeri/simboli)")
            self.strength_label.setStyleSheet("color: #ff9800; font-size: 11px;")
        elif strength <= 2:
            self.strength_label.setText("✓ Valida (Media)")
            self.strength_label.setStyleSheet("color: #2196F3; font-size: 11px;")
        else:
            self.strength_label.setText("✓ Valida (Forte)")
            self.strength_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        
        self.export_btn.setEnabled(True)
    
    def export_keys(self):
        """Export master keys to encrypted archive"""
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        
        # Validate password (should already be done by validate_passphrase but double-check)
        if len(password) < 16:
            QMessageBox.warning(
                self,
                "Password Troppo Corta",
                "La password deve essere di almeno 16 caratteri."
            )
            return
        
        if password != confirm:
            QMessageBox.warning(
                self,
                "Password Non Coincidono",
                "Le due password non coincidono."
            )
            return
        
        # Select destination
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salva Chiavi di Recupero",
            "chiavi_recupero_abbonamenti_protette.enc",
            "Encrypted Archive (*.enc);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            # Create temporary zip
            import tempfile
            temp_zip = Path(tempfile.gettempdir()) / "temp_keys.zip"
            
            with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all key files
                for key_file in self.keys_dir.iterdir():
                    if key_file.is_file() and key_file.suffix in ['.bin', '.pem']:
                        zipf.write(key_file, f"keys/{key_file.name}")
            
            # Encrypt the zip (always encrypted now)
            with open(temp_zip, 'rb') as f:
                zip_data = f.read()
            
            # Derive key and encrypt
            key, salt = derive_key_from_passphrase(password)
            encrypted_data = encrypt_with_key(zip_data, key)
            
            # Write encrypted file with metadata
            with open(file_path, 'wb') as f:
                f.write(b'87029')  # Magic header
                f.write(b'\x02')  # Version 2 (key export)
                f.write(salt)
                f.write(encrypted_data)
            
            # Cleanup
            temp_zip.unlink()
            
            # Store for recovery sheet
            self.last_export_path = file_path
            self.last_password = password
            
            # Show success message
            QMessageBox.information(
                self,
                "Esportazione Completata",
                f"Chiavi esportate con successo:\n\n{file_path}"
            )
            
            # Generate recovery sheet automatically
            self.generate_recovery_sheet()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Errore Esportazione",
                f"Impossibile esportare le chiavi:\n\n{str(e)}"
            )
    
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
            recovery_path = recovery_dir / f"recovery_sheet_keys_{timestamp}.pdf"
            
            # Generate PDF
            backup_location = (
                f"File chiavi: {self.last_export_path}\n\n"
                "Conservare su almeno 2 chiavette USB in cassaforte."
            )
            
            success = generate_recovery_sheet_pdf(
                password=self.last_password,
                backup_location=backup_location,
                output_path=recovery_path,
                sheet_type="keys"
            )
            
            if success:
                # Open PDF in default viewer automatically
                os.startfile(str(recovery_path))
                
                # Ask if user wants to open keys folder
                reply = QMessageBox.question(
                    self,
                    "Scheda Generata",
                    "La scheda di recupero è stata generata e aperta.\n\n"
                    "Vuoi aprire la cartella dove sono state salvate le chiavi?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    os.startfile(str(Path(self.last_export_path).parent))
                
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
