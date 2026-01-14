from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Subscription:
    protocol_id: str
    owner_name: str
    license_plate: str
    email: str
    address: str
    mobile: str
    subscription_start: datetime
    subscription_end: datetime
    payment_details: float
    payment_method: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "protocol_id": self.protocol_id,
            "owner_name": self.owner_name,
            "license_plate": self.license_plate,
            "email": self.email,
            "address": self.address,
            "mobile": self.mobile,
            "subscription_start": self.subscription_start.isoformat(),
            "subscription_end": self.subscription_end.isoformat(),
            "payment_details": self.payment_details,
            "payment_method": self.payment_method,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class AuditLogEntry:
    id: int
    operation_type: str
    protocol_id: str
    timestamp: datetime
    user: str
    reason: str
    before_data: Optional[dict]
    after_data: Optional[dict]
    ip_address: Optional[str] = None
    computer_name: Optional[str] = None


class Schema:
    @staticmethod
    def get_create_tables_sql() -> list[str]:
        return [
            Schema._subscriptions_table(),
            Schema._audit_log_table(),
            Schema._data_integrity_table(),
        ]

    @staticmethod
    def get_create_indexes_sql() -> list[str]:
        return [
            Schema._subscriptions_indexes(),
            Schema._audit_log_indexes(),
        ]

    @staticmethod
    def _subscriptions_table() -> str:
        return """
        CREATE TABLE IF NOT EXISTS subscriptions (
            protocol_id TEXT PRIMARY KEY,
            owner_name TEXT NOT NULL,
            license_plate TEXT NOT NULL,
            email_encrypted BLOB,
            address_encrypted BLOB,
            mobile_encrypted BLOB,
            subscription_start TEXT NOT NULL,
            subscription_end TEXT NOT NULL,
            payment_details_encrypted BLOB,
            payment_method TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """

    @staticmethod
    def _audit_log_table() -> str:
        return """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL CHECK(operation_type IN ('INSERT', 'UPDATE', 'DELETE')),
            protocol_id TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            user TEXT NOT NULL,
            reason TEXT NOT NULL,
            before_data TEXT,
            after_data TEXT,
            ip_address TEXT,
            computer_name TEXT
        )
        """

    @staticmethod
    def _data_integrity_table() -> str:
        return """
        CREATE TABLE IF NOT EXISTS data_integrity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id TEXT NOT NULL,
            signature BLOB NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(table_name, record_id)
        )
        """

    @staticmethod
    def _subscriptions_indexes() -> str:
        return """
        CREATE INDEX IF NOT EXISTS idx_license_plate
        ON subscriptions(license_plate);

        CREATE INDEX IF NOT EXISTS idx_dates
        ON subscriptions(subscription_start, subscription_end);

        CREATE INDEX IF NOT EXISTS idx_owner_name
        ON subscriptions(owner_name);

        CREATE INDEX IF NOT EXISTS idx_address
        ON subscriptions(address_encrypted);

        CREATE INDEX IF NOT EXISTS idx_mobile
        ON subscriptions(mobile_encrypted);
        """

    @staticmethod
    def _audit_log_indexes() -> str:
        return """
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp
        ON audit_log(timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_audit_protocol
        ON audit_log(protocol_id);

        CREATE INDEX IF NOT EXISTS idx_audit_operation
        ON audit_log(operation_type);

        CREATE INDEX IF NOT EXISTS idx_audit_user
        ON audit_log(user);
        """
