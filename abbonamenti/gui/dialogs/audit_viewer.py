import json
from typing import List, Optional

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from abbonamenti.database.manager import DatabaseManager
from abbonamenti.database.schema import AuditLogEntry
from abbonamenti.utils.paths import get_database_path, get_keys_dir


class AuditLogModel(QAbstractTableModel):
    def __init__(self, entries: Optional[List[AuditLogEntry]] = None):
        super().__init__()
        self.entries: List[AuditLogEntry] = [] if entries is None else entries
        self.headers = [
            "Timestamp",
            "Operazione",
            "ID Protocollo",
            "Utente",
            "Motivo",
            "Dettagli",
        ]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.entries)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        entry = self.entries[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            if column == 0:
                return entry.timestamp.strftime("%d/%m/%Y %H:%M:%S")
            elif column == 1:
                return entry.operation_type
            elif column == 2:
                return entry.protocol_id
            elif column == 3:
                return entry.user
            elif column == 4:
                return (
                    entry.reason[:50] + "..."
                    if len(entry.reason) > 50
                    else entry.reason
                )
            elif column == 5:
                return "Visualizza"

        elif role == Qt.BackgroundRole:
            if column == 1:
                if entry.operation_type == "INSERT":
                    return QColor(200, 230, 200)
                elif entry.operation_type == "UPDATE":
                    return QColor(230, 230, 200)
                elif entry.operation_type == "DELETE":
                    return QColor(255, 200, 200)

        elif role == Qt.TextAlignmentRole:
            if column in [0, 1, 5]:
                return Qt.AlignCenter

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ):
        if (
            role == Qt.DisplayRole and orientation == Qt.Horizontal
        ):
            return self.headers[section]
        return None

    def update_data(self, entries: List[AuditLogEntry]):
        self.beginResetModel()
        self.entries = entries
        self.endResetModel()


class AuditLogViewer(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager(get_database_path(), get_keys_dir())
        self.model = AuditLogModel(self.db_manager.get_audit_log_entries())
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Log Audit - Sola Lettura")
        self.setMinimumSize(1000, 600)

        layout = QVBoxLayout(self)

        filter_layout = QHBoxLayout()

        self.operation_combo = QComboBox()
        self.operation_combo.addItems(["Tutti", "INSERT", "UPDATE", "DELETE"])
        self.operation_combo.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Operazione:"))
        filter_layout.addWidget(self.operation_combo)

        filter_layout.addSpacing(20)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cerca...")
        self.search_input.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Cerca:"))
        filter_layout.addWidget(self.search_input)

        filter_layout.addStretch()

        self.export_csv_btn = QPushButton("Esporta CSV")
        self.export_csv_btn.clicked.connect(self.export_csv)
        filter_layout.addWidget(self.export_csv_btn)

        self.close_btn = QPushButton("Chiudi")
        self.close_btn.clicked.connect(self.accept)
        filter_layout.addWidget(self.close_btn)

        layout.addLayout(filter_layout)

        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setColumnWidth(0, 150)
        self.table_view.setColumnWidth(1, 100)
        self.table_view.setColumnWidth(2, 120)
        self.table_view.setColumnWidth(3, 150)
        self.table_view.setColumnWidth(4, 300)
        self.table_view.setColumnWidth(5, 80)

        layout.addWidget(self.table_view)

    @pyqtSlot()
    def apply_filters(self):
        operation = self.operation_combo.currentText()
        search_text = self.search_input.text()

        all_entries = self.db_manager.get_audit_log_entries(limit=1000)

        filtered_entries = []
        for entry in all_entries:
            if operation != "Tutti" and entry.operation_type != operation:
                continue

            if search_text:
                search_lower = search_text.lower()
                if (
                    search_lower not in entry.protocol_id.lower()
                    and search_lower not in entry.user.lower()
                    and search_lower not in entry.reason.lower()
                ):
                    continue

            filtered_entries.append(entry)

        self.model.update_data(filtered_entries)

    @pyqtSlot()
    def export_csv(self):
        import csv

        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Esporta Log Audit",
            "",
            "File CSV (*.csv)",
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Timestamp",
                        "Operazione",
                        "ID Protocollo",
                        "Utente",
                        "Motivo",
                        "Computer",
                        "IP",
                        "Dati Prima",
                        "Dati Dopo",
                    ]
                )

                for entry in self.model.entries:
                    before_json = (
                        json.dumps(entry.before_data, ensure_ascii=False)
                        if entry.before_data
                        else ""
                    )
                    after_json = (
                        json.dumps(entry.after_data, ensure_ascii=False)
                        if entry.after_data
                        else ""
                    )

                    writer.writerow(
                        [
                            entry.timestamp.isoformat(),
                            entry.operation_type,
                            entry.protocol_id,
                            entry.user,
                            entry.reason,
                            entry.computer_name or "",
                            entry.ip_address or "",
                            before_json,
                            after_json,
                        ]
                    )

            QMessageBox.information(
                self, "Successo", "Log audit esportato con successo!"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Errore", f"Errore durante l'esportazione: {str(e)}"
            )
