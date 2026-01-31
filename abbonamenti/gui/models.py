from datetime import datetime
from typing import List, Optional

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QColor

from abbonamenti.database.schema import Subscription


class SubscriptionsTableModel(QAbstractTableModel):
    def __init__(self, subscriptions: Optional[List[Subscription]] = None):
        super().__init__()
        self.subscriptions: List[Subscription] = (
            [] if subscriptions is None else subscriptions
        )
        self.headers = [
            "ID Protocollo",
            "Nome Proprietario",
            "Targa",
            "Email",
            "Indirizzo",
            "Cellulare",
            "Data Inizio",
            "Data Fine",
            "Metodo Pagamento",
            "Importo Pagato",
            "Stato",
        ]
        self.sort_column = 0
        self.sort_order = Qt.AscendingOrder

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.subscriptions)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        subscription = self.subscriptions[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            if column == 0:
                return subscription.protocol_id
            elif column == 1:
                return subscription.owner_name
            elif column == 2:
                return subscription.license_plate
            elif column == 3:
                return subscription.email if subscription.email else ""
            elif column == 4:
                return subscription.address if subscription.address else ""
            elif column == 5:
                return subscription.mobile if subscription.mobile else ""
            elif column == 6:
                return subscription.subscription_start.strftime("%d/%m/%Y")
            elif column == 7:
                return subscription.subscription_end.strftime("%d/%m/%Y")
            elif column == 8:
                return subscription.payment_method
            elif column == 9:
                return f"€ {subscription.payment_details:.2f}"
            elif column == 10:
                return self._get_status(subscription)

        elif role == Qt.BackgroundRole:
            if column == 10:
                status = self._get_status(subscription)
                if status == "Attivo":
                    return QColor(200, 255, 200)
                elif status == "In scadenza":
                    return QColor(255, 255, 200)
                elif status == "Scaduto":
                    return QColor(255, 200, 200)
                elif status == "Non ancora attivo":
                    return QColor(220, 220, 255)

        elif role == Qt.TextAlignmentRole:
            if column in [6, 7, 8, 9, 10]:
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

    def _get_status(self, subscription: Subscription) -> str:
        today = datetime.now().date()
        start_date = subscription.subscription_start.date()
        end_date = subscription.subscription_end.date()

        if start_date > today:
            return "Non ancora attivo"
        elif end_date < today:
            return "Scaduto"
        elif (end_date - today).days <= 30:
            return "In scadenza"
        else:
            return "Attivo"

    def update_data(self, subscriptions: List[Subscription]):
        self.beginResetModel()
        self.subscriptions = subscriptions
        self.endResetModel()

    def sort(self, column: int, order: int = Qt.AscendingOrder):
        """Sort table by column while preserving current data."""
        reverse = order == Qt.DescendingOrder

        def sort_key(sub: Subscription):
            if column == 0:
                return sub.protocol_id
            if column == 1:
                return sub.owner_name.lower()
            if column == 2:
                return sub.license_plate
            if column == 3:
                return sub.email or ""
            if column == 4:
                return sub.address or ""
            if column == 5:
                return sub.mobile or ""
            if column == 6:
                return sub.subscription_start
            if column == 7:
                return sub.subscription_end
            if column == 8:
                return sub.payment_method
            if column == 9:
                return sub.payment_details
            if column == 10:
                status = self._get_status(sub)
                return status
            return 0

        self.layoutAboutToBeChanged.emit()
        self.subscriptions.sort(key=sort_key, reverse=reverse)
        self.layoutChanged.emit()
