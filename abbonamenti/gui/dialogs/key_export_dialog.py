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
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
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
        
        # Protection options
        protection_group = QGroupBox("Protezione Chiavi")
        protection_layout = QVBoxLayout(protection_group)
        
        info_label = QLabel(
            "Le chiavi verranno esportate in un archivio ZIP.\n"
            "Puoi proteggerlo con una password aggiuntiva (consigliato)."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 8px;")
        protection_layout.addWidget(info_label)
        
        self.password_check = QCheckBox("Proteggi con password (consigliato)")
        self.password_check.setChecked(True)
        self.password_check.toggled.connect(self.toggle_password)
        protection_layout.addWidget(self.password_check)
        
        pass_form = QFormLayout()
        pass_form.setSpacing(12)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Minimo 16 caratteri")
        pass_form.addRow("Password *:", self.password_input)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("Conferma password")
        pass_form.addRow("Conferma *:", self.confirm_input)
        
        protection_layout.addLayout(pass_form)
        
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
        self.export_btn.clicked.connect(self.export_keys)
        self.export_btn.setStyleSheet(
            "QPushButton { background: #c62828; color: white; font-weight: bold; "
            "padding: 10px 24px; font-size: 13px; } "
            "QPushButton:hover { background: #b71c1c; }"
        )
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
    
    def toggle_password(self, checked: bool):
        """Toggle password fields"""
        self.password_input.setEnabled(checked)
        self.confirm_input.setEnabled(checked)
    
    def export_keys(self):
        """Export master keys to encrypted archive"""
        # Validate password if enabled
        if self.password_check.isChecked():
            password = self.password_input.text()
            confirm = self.confirm_input.text()
            
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
        suggested_name = f"chiavi_recupero_abbonamenti.zip"
        if self.password_check.isChecked():
            suggested_name = f"chiavi_recupero_abbonamenti_protette.enc"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salva Chiavi di Recupero",
            suggested_name,
            "Archive Files (*.zip *.enc);;All Files (*)"
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
            
            # If password protection enabled, encrypt the zip
            if self.password_check.isChecked():
                with open(temp_zip, 'rb') as f:
                    zip_data = f.read()
                
                # Derive key and encrypt
                key, salt = derive_key_from_passphrase(password)
                encrypted_data = encrypt_with_key(zip_data, key)
                
                # Write encrypted file with metadata
                with open(file_path, 'wb') as f:
                    f.write(b'\x02')  # Version 2 (key export)
                    f.write(salt)
                    f.write(encrypted_data)
            else:
                # Just copy the zip
                import shutil
                shutil.copy2(temp_zip, file_path)
            
            # Cleanup
            temp_zip.unlink()
            
            # Success message
            QMessageBox.information(
                self,
                "Esportazione Completata",
                f"✅ Chiavi esportate con successo!\n\n"
                f"File: {file_path}\n\n"
                f"⚠️ RICORDA:\n"
                f"• Copia questo file su almeno 2 chiavette USB\n"
                f"• Conservale in luoghi sicuri e separati\n"
                f"• Senza queste chiavi, i backup sono inutili!"
            )
            
            # Ask if user wants to open folder
            reply = QMessageBox.question(
                self,
                "Aprire Cartella?",
                "Vuoi aprire la cartella dove sono state salvate le chiavi?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(str(Path(file_path).parent))
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Errore Esportazione",
                f"Impossibile esportare le chiavi:\n\n{str(e)}"
            )
