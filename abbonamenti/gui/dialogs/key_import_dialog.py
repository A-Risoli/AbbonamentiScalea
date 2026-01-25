"""Dialog for restoring master encryption keys from backup (.enc or .zip)."""
from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from abbonamenti.gui.styles import get_stylesheet
from abbonamenti.security.crypto import (
    decrypt_with_key,
    derive_key_from_passphrase,
)


class KeyImportDialog(QDialog):
    """Simple wizard to import recovery keys without using the terminal."""

    def __init__(self, keys_dir: Path, parent=None):
        super().__init__(parent)
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.setWindowTitle("Ripristina Chiavi di Recupero")
        self.setMinimumWidth(520)
        self.setStyleSheet(get_stylesheet())
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        warning = QLabel(
            "🔑 Ripristino Chiavi di Cifratura\n\n"
            "Senza queste chiavi i backup NON si aprono.\n"
            "Seleziona il file di chiavi (.enc protetto o .zip) e inserisci la"
            " password se richiesta."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "color: #b71c1c; background: #ffebee; padding: 10px; "
            "border: 1px solid #c62828; border-radius: 6px;"
        )
        layout.addWidget(warning)

        form = QFormLayout()
        form.setSpacing(10)

        file_row = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Seleziona file .enc o .zip")
        browse_btn = QPushButton("Sfoglia")
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(self.file_input)
        file_row.addWidget(browse_btn)
        form.addRow("File chiavi:", file_row)

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Password esportazione (se protetto)")
        form.addRow("Password:", self.pass_input)

        layout.addLayout(form)

        help_box = QGroupBox("Suggerimenti")
        help_layout = QVBoxLayout(help_box)
        tips = QLabel(
            "• Accettiamo sia .enc (protetto) che .zip (non protetto)\n"
            "• Per .enc la password è obbligatoria (minimo 16 caratteri)\n"
            "• Le chiavi vengono copiate in %APPDATA%/AbbonamentiScalea/keys"
        )
        tips.setWordWrap(True)
        tips.setStyleSheet("color: #555; padding: 6px;")
        help_layout.addWidget(tips)
        layout.addWidget(help_box)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        import_btn = QPushButton("Ripristina Chiavi")
        import_btn.clicked.connect(self._import_keys)
        import_btn.setStyleSheet(
            "QPushButton { background: #2e7d32; color: white; font-weight: bold; "
            "padding: 9px 18px; } "
            "QPushButton:hover { background: #1b5e20; }"
        )
        buttons.addWidget(cancel_btn)
        buttons.addWidget(import_btn)
        layout.addLayout(buttons)

    def _browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleziona file chiavi",
            "",
            "Key Backups (*.enc *.zip);;Tutti i file (*)",
        )
        if file_path:
            self.file_input.setText(file_path)
            self._toggle_password(Path(file_path))

    def _toggle_password(self, path: Path):
        needs_password = path.suffix.lower() == ".enc"
        self.pass_input.setEnabled(needs_password)
        if not needs_password:
            self.pass_input.clear()

    def _import_keys(self):
        from abbonamenti.utils.paths import get_keys_dir

        path_str = self.file_input.text().strip()
        if not path_str:
            QMessageBox.warning(self, "Seleziona File", "Seleziona il file di chiavi.")
            return

        source = Path(path_str)
        if not source.exists():
            QMessageBox.warning(self, "File mancante", "Il file indicato non esiste.")
            return

        if source.suffix.lower() not in {".enc", ".zip"}:
            QMessageBox.warning(
                self,
                "Formato non valido",
                "Sono accettati solo file .enc (protetti) o .zip (non protetti).",
            )
            return

        try:
            zip_bytes: bytes
            if source.suffix.lower() == ".enc":
                data = source.read_bytes()
                if not data:
                    raise ValueError("File vuoto")

                # Check magic header
                if len(data) < 5:
                    raise ValueError("File non valido (troppo corto)")
                
                magic = data[0:5]
                if magic != b"87029":
                    raise ValueError("File non valido: non è un backup di AbbonaMunicipale")
                
                # Detect format after magic header
                header = data[5]
                if header == 0x02:
                    # Key export (encrypted, version 2)
                    salt = data[6:38]
                    payload = data[38:]

                    password = self.pass_input.text()
                    if len(password) < 16:
                        raise ValueError("Password minima: 16 caratteri")

                    key, _ = derive_key_from_passphrase(password, salt)
                    zip_bytes = decrypt_with_key(payload, key)
                elif header == 0x01:
                    # Database backup (version 1) - cannot import as keys
                    raise ValueError(
                        "Hai selezionato un backup del database (.enc v1).\n"
                        "Per ripristinare il database usa 'Ripristina Backup'.\n"
                        "Per le chiavi usa il file esportato da 'Esporta Chiave di Recupero'."
                    )
                else:
                    raise ValueError(
                        f"Formato backup non riconosciuto (versione {header})."
                    )
            else:
                zip_bytes = source.read_bytes()

            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = Path(tmpdir) / "keys.zip"
                zip_path.write_bytes(zip_bytes)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    members = [m for m in zf.namelist() if m.startswith("keys/")]
                    if not members:
                        raise ValueError("Archivio non contiene la cartella 'keys/'")

                    target_dir = Path(get_keys_dir())
                    target_dir.mkdir(parents=True, exist_ok=True)

                    for member in members:
                        if member.endswith("/"):
                            continue
                        name = Path(member).name
                        dest = target_dir / name
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            shutil.copyfileobj(src, dst)

            QMessageBox.information(
                self,
                "Ripristino completato",
                "Chiavi ripristinate correttamente. Ora puoi aprire i backup cifrati.",
            )

            reply = QMessageBox.question(
                self,
                "Aprire la cartella?",
                "Vuoi aprire la cartella delle chiavi?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(str(self.keys_dir))

            self.accept()

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "Errore ripristino",
                f"Impossibile ripristinare le chiavi:\n\n{exc}",
            )

