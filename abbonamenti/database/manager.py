import base64

import json
import os
import shutil
import socket
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from abbonamenti.database.schema import AuditLogEntry, Schema, Subscription
from abbonamenti.security.crypto import CryptoManager, derive_key_from_passphrase, encrypt_with_key, decrypt_with_key
from abbonamenti.security.hmac import HMACManager

# Magic header to identify valid backup files
_BACKUP_MAGIC_HEADER = b"87029"


class DatabaseManager:
    def __init__(self, db_path: Path, keys_dir: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.crypto = CryptoManager(keys_dir)
        self.hmac = HMACManager(keys_dir)
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enable WAL mode for concurrent read access (GUI + bot)
        cursor.execute("PRAGMA journal_mode=WAL")

        for sql in Schema.get_create_tables_sql():
            cursor.execute(sql)

        for sql in Schema.get_create_indexes_sql():
            cursor.executescript(sql)

        conn.commit()
        conn.close()

    def _get_current_user_info(self) -> dict:
        return {
            "user": os.getlogin(),
            "computer_name": socket.gethostname(),
            "ip_address": socket.gethostbyname(socket.gethostname()),
        }

    def _get_protocol_id(self) -> str:
        year = datetime.now().year
        year_short = str(year)[2:]
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for new format (YYYY-XXXXXXXXXX)
        cursor.execute(
            "SELECT protocol_id FROM subscriptions WHERE protocol_id LIKE ? ORDER BY protocol_id DESC LIMIT 1",
            (f"{year}-%",),
        )
        result_new = cursor.fetchone()
        
        # Check for old format (SUB-YY-XXXX) for backward compatibility
        cursor.execute(
            "SELECT protocol_id FROM subscriptions WHERE protocol_id LIKE ? ORDER BY protocol_id DESC LIMIT 1",
            (f"SUB-{year_short}-%",),
        )
        result_old = cursor.fetchone()
        
        conn.close()

        # Determine the highest sequence number from both formats
        new_id = 0
        
        if result_new:
            # Parse new format: 2026-0000000001 -> 1
            new_id = max(new_id, int(result_new[0].split("-")[1]))
        
        if result_old:
            # Parse old format: SUB-26-0001 -> 1
            new_id = max(new_id, int(result_old[0].split("-")[2]))
        
        new_id += 1
        return f"{year}-{new_id:010d}"

    def _update_integrity_signature(self, protocol_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM subscriptions WHERE protocol_id = ?", (protocol_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            columns = [
                "protocol_id",
                "owner_name",
                "license_plate",
                "email_encrypted",
                "address_encrypted",
                "mobile_encrypted",
                "subscription_start",
                "subscription_end",
                "payment_details_encrypted",
                "payment_method",
                "created_at",
                "updated_at",
            ]
            data = dict(zip(columns, row))
            data["email_encrypted"] = base64.b64encode(data["email_encrypted"]).decode(
                "utf-8"
            )
            data["address_encrypted"] = base64.b64encode(
                data["address_encrypted"]
            ).decode("utf-8")
            data["mobile_encrypted"] = base64.b64encode(
                data["mobile_encrypted"]
            ).decode("utf-8")
            data["payment_details_encrypted"] = base64.b64encode(
                data["payment_details_encrypted"]
            ).decode("utf-8")
            signature = self.hmac.generate_hmac(data)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO data_integrity 
                (table_name, record_id, signature, created_at) 
                VALUES (?, ?, ?, ?)""",
                ("subscriptions", protocol_id, signature, datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()

    def add_subscription(
        self,
        owner_name: str,
        license_plate: str,
        email: str,
        address: str,
        mobile: str,
        subscription_start: datetime,
        subscription_end: datetime,
        payment_details: float,
        payment_method: str,
        reason: str,
    ) -> str:
        payment_method = payment_method.strip().upper()
        protocol_id = self._get_protocol_id()
        now = datetime.now().isoformat()
        user_info = self._get_current_user_info()

        email_encrypted = self.crypto.encrypt(email)
        address_encrypted = self.crypto.encrypt(address)
        mobile_encrypted = self.crypto.encrypt(mobile)
        payment_details_encrypted = self.crypto.encrypt(str(payment_details))

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        subscription_data = {
            "protocol_id": protocol_id,
            "owner_name": owner_name,
            "license_plate": license_plate,
            "email": email,
            "address": address,
            "mobile": mobile,
            "subscription_start": subscription_start.isoformat(),
            "subscription_end": subscription_end.isoformat(),
            "payment_details": payment_details,
            "payment_method": payment_method,
            "created_at": now,
            "updated_at": now,
        }

        cursor.execute(
            """INSERT INTO subscriptions 
            (protocol_id, owner_name, license_plate, email_encrypted, 
             address_encrypted, mobile_encrypted,
             subscription_start, subscription_end, payment_details_encrypted, 
             payment_method, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                protocol_id,
                owner_name,
                license_plate,
                email_encrypted,
                address_encrypted,
                mobile_encrypted,
                subscription_start.isoformat(),
                subscription_end.isoformat(),
                payment_details_encrypted,
                payment_method,
                now,
                now,
            ),
        )

        conn.commit()
        conn.close()

        self._update_integrity_signature(protocol_id)

        self._add_audit_log(
            operation_type="INSERT",
            protocol_id=protocol_id,
            reason=reason,
            before_data=None,
            after_data=subscription_data,
            user_info=user_info,
        )

        return protocol_id

    def update_subscription(
        self,
        protocol_id: str,
        owner_name: str,
        license_plate: str,
        email: str,
        address: str,
        mobile: str,
        subscription_start: datetime,
        subscription_end: datetime,
        payment_details: float,
        payment_method: str,
        reason: str,
    ) -> bool:
        payment_method = payment_method.strip().upper()
        before_data = self.get_subscription_raw(protocol_id)
        if not before_data:
            return False

        now = datetime.now().isoformat()
        user_info = self._get_current_user_info()

        email_encrypted = self.crypto.encrypt(email)
        address_encrypted = self.crypto.encrypt(address)
        mobile_encrypted = self.crypto.encrypt(mobile)
        payment_details_encrypted = self.crypto.encrypt(str(payment_details))

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """UPDATE subscriptions SET 
            owner_name = ?, license_plate = ?, email_encrypted = ?,
            address_encrypted = ?, mobile_encrypted = ?,
            subscription_start = ?, subscription_end = ?, 
            payment_details_encrypted = ?, payment_method = ?, updated_at = ?
            WHERE protocol_id = ?""",
            (
                owner_name,
                license_plate,
                email_encrypted,
                address_encrypted,
                mobile_encrypted,
                subscription_start.isoformat(),
                subscription_end.isoformat(),
                payment_details_encrypted,
                payment_method,
                now,
                protocol_id,
            ),
        )

        conn.commit()
        conn.close()

        self._update_integrity_signature(protocol_id)

        after_data = self.get_subscription_raw(protocol_id)

        self._add_audit_log(
            operation_type="UPDATE",
            protocol_id=protocol_id,
            reason=reason,
            before_data=before_data,
            after_data=after_data,
            user_info=user_info,
        )

        return True

    def delete_subscription(self, protocol_id: str, reason: str) -> bool:
        before_data = self.get_subscription_raw(protocol_id)
        if not before_data:
            return False

        user_info = self._get_current_user_info()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM subscriptions WHERE protocol_id = ?", (protocol_id,)
        )
        cursor.execute("DELETE FROM data_integrity WHERE record_id = ?", (protocol_id,))
        conn.commit()
        conn.close()

        self._add_audit_log(
            operation_type="DELETE",
            protocol_id=protocol_id,
            reason=reason,
            before_data=before_data,
            after_data=None,
            user_info=user_info,
        )

        return True

    def get_subscription_raw(self, protocol_id: str) -> Optional[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM subscriptions WHERE protocol_id = ?", (protocol_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return dict(row)

    def get_subscription(self, protocol_id: str) -> Optional[Subscription]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM subscriptions WHERE protocol_id = ?", (protocol_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        email = self.crypto.decrypt(row["email_encrypted"])
        address = self.crypto.decrypt(row["address_encrypted"])
        mobile = self.crypto.decrypt(row["mobile_encrypted"])
        payment_details_str = self.crypto.decrypt(row["payment_details_encrypted"])
        payment_details = float(payment_details_str)

        return Subscription(
            protocol_id=row["protocol_id"],
            owner_name=row["owner_name"],
            license_plate=row["license_plate"],
            email=email,
            address=address,
            mobile=mobile,
            subscription_start=datetime.fromisoformat(row["subscription_start"]),
            subscription_end=datetime.fromisoformat(row["subscription_end"]),
            payment_details=payment_details,
            payment_method=row["payment_method"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _get_subscriptions_for_stats(
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> List[Dict[str, object]]:
        """
        Lightweight query for statistics - only decrypts payment_details.
        Returns dict with minimal fields needed for analytics.
        Optionally filters by subscription_start date range.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query with optional date filtering on subscription_start
        query = """SELECT protocol_id, subscription_start, subscription_end,
                      payment_details_encrypted, payment_method, created_at
               FROM subscriptions"""
        params = []
        
        if date_from or date_to:
            where_clauses = []
            if date_from:
                where_clauses.append("subscription_start >= ?")
                params.append(date_from.isoformat())
            if date_to:
                where_clauses.append("subscription_start <= ?")
                params.append(date_to.isoformat())
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY protocol_id"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        subscriptions = []
        for row in rows:
            payment_details_str = self.crypto.decrypt(row["payment_details_encrypted"])
            payment_details = float(payment_details_str)

            subscriptions.append({
                "protocol_id": row["protocol_id"],
                "subscription_start": datetime.fromisoformat(row["subscription_start"]),
                "subscription_end": datetime.fromisoformat(row["subscription_end"]),
                "payment_details": payment_details,
                "payment_method": row["payment_method"],
            })

        return subscriptions

    @staticmethod
    def _normalize_payment_method(method: str) -> str:
        """Normalize payment method variants to canonical labels."""
        if not method:
            return ""
        normalized = method.strip().upper()
        # Common variants mapping
        if normalized in {"POS", "CARD", "CARTE", "CARTA"}:
            return "POS"
        if normalized.startswith("BOLL") or normalized.startswith("BOL"):
            return "BOLLETTINO"
        return normalized

    def get_all_subscriptions(self) -> List[Subscription]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions ORDER BY protocol_id")
        rows = cursor.fetchall()
        conn.close()

        subscriptions = []
        for row in rows:
            email = self.crypto.decrypt(row["email_encrypted"])
            address = self.crypto.decrypt(row["address_encrypted"])
            mobile = self.crypto.decrypt(row["mobile_encrypted"])
            payment_details_str = self.crypto.decrypt(row["payment_details_encrypted"])
            payment_details = float(payment_details_str)

            subscriptions.append(
                Subscription(
                    protocol_id=row["protocol_id"],
                    owner_name=row["owner_name"],
                    license_plate=row["license_plate"],
                    email=email,
                    address=address,
                    mobile=mobile,
                    subscription_start=datetime.fromisoformat(
                        row["subscription_start"]
                    ),
                    subscription_end=datetime.fromisoformat(row["subscription_end"]),
                    payment_details=payment_details,
                    payment_method=row["payment_method"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
            )

        return subscriptions

    def search_subscriptions(self, query: str) -> List[Subscription]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM subscriptions
            WHERE protocol_id LIKE ?
               OR owner_name LIKE ?
               OR license_plate LIKE ?
            ORDER BY protocol_id""",
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        )
        rows = cursor.fetchall()
        conn.close()

        subscriptions = []
        for row in rows:
            email = self.crypto.decrypt(row["email_encrypted"])
            address = self.crypto.decrypt(row["address_encrypted"])
            mobile = self.crypto.decrypt(row["mobile_encrypted"])
            payment_details_str = self.crypto.decrypt(row["payment_details_encrypted"])
            payment_details = float(payment_details_str)

            subscriptions.append(
                Subscription(
                    protocol_id=row["protocol_id"],
                    owner_name=row["owner_name"],
                    license_plate=row["license_plate"],
                    email=email,
                    address=address,
                    mobile=mobile,
                    subscription_start=datetime.fromisoformat(
                        row["subscription_start"]
                    ),
                    subscription_end=datetime.fromisoformat(row["subscription_end"]),
                    payment_details=payment_details,
                    payment_method=row["payment_method"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
            )

        return subscriptions

    def _add_audit_log(
        self,
        operation_type: str,
        protocol_id: str,
        reason: str,
        before_data: Optional[dict],
        after_data: Optional[dict],
        user_info: dict,
    ):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        before_json = json.dumps(before_data, default=str) if before_data else None
        after_json = json.dumps(after_data, default=str) if after_data else None

        cursor.execute(
            """INSERT INTO audit_log 
            (operation_type, protocol_id, user, reason, before_data, after_data, ip_address, computer_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                operation_type,
                protocol_id,
                user_info["user"],
                reason,
                before_json,
                after_json,
                user_info["ip_address"],
                user_info["computer_name"],
            ),
        )

        conn.commit()
        conn.close()

    def get_audit_log_entries(
        self, operation_type: Optional[str] = None, limit: int = 100
    ) -> List[AuditLogEntry]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if operation_type:
            cursor.execute(
                """SELECT * FROM audit_log 
                WHERE operation_type = ? 
                ORDER BY timestamp DESC 
                LIMIT ?""",
                (operation_type, limit),
            )
        else:
            cursor.execute(
                """SELECT * FROM audit_log 
                ORDER BY timestamp DESC 
                LIMIT ?""",
                (limit,),
            )

        rows = cursor.fetchall()
        conn.close()

        entries = []
        for row in rows:
            before_data = json.loads(row["before_data"]) if row["before_data"] else None
            after_data = json.loads(row["after_data"]) if row["after_data"] else None

            entries.append(
                AuditLogEntry(
                    id=row["id"],
                    operation_type=row["operation_type"],
                    protocol_id=row["protocol_id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    user=row["user"],
                    reason=row["reason"],
                    before_data=before_data,
                    after_data=after_data,
                    ip_address=row["ip_address"],
                    computer_name=row["computer_name"],
                )
            )

        return entries

    def verify_data_integrity(self) -> Tuple[bool, List[str]]:
        issues = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM subscriptions")
        rows = cursor.fetchall()

        for row in rows:
            protocol_id = row[0]
            columns = [
                "protocol_id",
                "owner_name",
                "license_plate",
                "email_encrypted",
                "address_encrypted",
                "mobile_encrypted",
                "subscription_start",
                "subscription_end",
                "payment_details_encrypted",
                "payment_method",
                "created_at",
                "updated_at",
            ]
            data = dict(zip(columns, row))
            data["email_encrypted"] = base64.b64encode(data["email_encrypted"]).decode(
                "utf-8"
            )
            data["address_encrypted"] = base64.b64encode(
                data["address_encrypted"]
            ).decode("utf-8")
            data["mobile_encrypted"] = base64.b64encode(
                data["mobile_encrypted"]
            ).decode("utf-8")
            data["payment_details_encrypted"] = base64.b64encode(
                data["payment_details_encrypted"]
            ).decode("utf-8")

            cursor.execute(
                "SELECT signature FROM data_integrity WHERE record_id = ?",
                (protocol_id,),
            )
            signature_row = cursor.fetchone()

            if not signature_row:
                issues.append(f"Missing integrity signature for {protocol_id}")
                continue

            stored_signature = signature_row[0]
            if not self.hmac.verify_hmac(data, stored_signature):
                issues.append(f"Integrity check failed for {protocol_id}")

        conn.close()
        return len(issues) == 0, issues

    def get_payment_statistics(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, object]:
        """Get payment statistics for a given year and/or month, or date range"""
        # Use lightweight query for performance
        subs = self._get_subscriptions_for_stats(date_from, date_to)
        
        # Filter by year and month only if date_from/date_to not specified
        # (to avoid double filtering with inconsistent criteria)
        filtered_subs = []
        for sub in subs:
            # If using date range filter, skip year/month filter
            if date_from is None and date_to is None:
                if year and sub["subscription_start"].year != year:
                    continue
                if month and sub["subscription_start"].month != month:
                    continue
            filtered_subs.append(sub)

        # Calculate statistics
        total_revenue = sum(sub["payment_details"] for sub in filtered_subs)
        subscription_count = len(filtered_subs)
        average_payment = total_revenue / subscription_count if subscription_count > 0 else 0.0
        
        pos_count = 0
        bollettino_count = 0
        for sub in filtered_subs:
            method = sub.get("payment_method", "")
            method_normalized = self._normalize_payment_method(method)
            if method_normalized == "POS":
                pos_count += 1
            elif method_normalized == "BOLLETTINO":
                bollettino_count += 1

        return {
            "total_revenue": total_revenue,
            "subscription_count": subscription_count,
            "average_payment": average_payment,
            "pos_count": pos_count,
            "bollettino_count": bollettino_count,
        }

    def get_monthly_revenue(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> List[Tuple[str, float]]:
        """Get revenue grouped by month, respecting optional year/month filters"""
        subs = self._get_subscriptions_for_stats()

        # Filter by year and month if specified
        if year:
            subs = [sub for sub in subs if sub["subscription_start"].year == year]
        if month:
            subs = [sub for sub in subs if sub["subscription_start"].month == month]

        # Group by month (or single month if filtered)
        monthly: Dict[str, float] = {}
        for sub in subs:
            month_label = sub["subscription_start"].strftime("%b %Y")
            if month_label not in monthly:
                monthly[month_label] = 0.0
            monthly[month_label] += sub["payment_details"]

        # Sort by date label
        return sorted(monthly.items(), key=lambda x: x[0])

    def get_payment_methods_breakdown(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> Dict[str, int]:
        """Get count of subscriptions by payment method"""
        subs = self._get_subscriptions_for_stats()

        # Filter by year and month
        if year:
            subs = [sub for sub in subs if sub["subscription_start"].year == year]
        if month:
            subs = [sub for sub in subs if sub["subscription_start"].month == month]

        methods = {"POS": 0, "BOLLETTINO": 0}
        for sub in subs:
            method = sub.get("payment_method", "")
            method_normalized = self._normalize_payment_method(method)
            if method_normalized in methods:
                methods[method_normalized] += 1

        return methods

    def get_revenue_trend(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> List[Tuple[str, float]]:
        """Get cumulative revenue trend over time, respecting optional filters"""
        subs = self._get_subscriptions_for_stats()

        # Filter by year/month if specified
        if year:
            subs = [sub for sub in subs if sub["subscription_start"].year == year]
        if month:
            subs = [sub for sub in subs if sub["subscription_start"].month == month]

        # Sort by date
        subs = sorted(subs, key=lambda x: x["subscription_start"])

        # Calculate cumulative revenue
        cumulative = 0.0
        trend: List[Tuple[str, float]] = []
        for sub in subs:
            cumulative += sub["payment_details"]
            # Show date with year when spanning multiple years
            date_label = (
                sub["subscription_start"].strftime("%d/%m/%Y")
                if year is None
                else sub["subscription_start"].strftime("%d/%m")
            )
            trend.append((date_label, cumulative))

        return trend

    def get_subscriptions_per_month(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> List[Tuple[str, int]]:
        """Get count of subscriptions created per month, respecting filters"""
        subs = self._get_subscriptions_for_stats()

        # Filter by year/month if specified
        if year:
            subs = [sub for sub in subs if sub["subscription_start"].year == year]
        if month:
            subs = [sub for sub in subs if sub["subscription_start"].month == month]

        # Group by month
        monthly: Dict[str, int] = {}
        for sub in subs:
            month_label = sub["subscription_start"].strftime("%b %Y")
            if month_label not in monthly:
                monthly[month_label] = 0
            monthly[month_label] += 1

        # Sort by date label
        return sorted(monthly.items(), key=lambda x: x[0])

    def get_subscriptions_by_plate(
        self, license_plate: str
    ) -> List[Dict]:
        """
        Get all subscriptions for a specific license plate.
        
        Args:
            license_plate: The license plate to search for
            
        Returns:
            List of subscription dictionaries with decrypted start/end dates
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT protocol_id, owner_name, license_plate, 
               subscription_start, subscription_end
               FROM subscriptions 
               WHERE UPPER(license_plate) = UPPER(?)
               ORDER BY subscription_start""",
            (license_plate,),
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        subscriptions = []
        for row in rows:
            subscriptions.append({
                "protocol_id": row[0],
                "owner_name": row[1],
                "license_plate": row[2],
                "subscription_start": datetime.fromisoformat(row[3]),
                "subscription_end": datetime.fromisoformat(row[4]),
            })
        
        return subscriptions

    def bulk_add_subscriptions(
        self,
        subscriptions: List[Dict],
        reason: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Add multiple subscriptions in a single transaction.
        
        Args:
            subscriptions: List of subscription dictionaries with keys:
                owner_name, license_plate, email, address, mobile,
                subscription_start, subscription_end, payment_details, payment_method
            reason: Audit log reason for all subscriptions
            progress_callback: Optional callback(current, total) for progress updates
            
        Returns:
            Tuple of (success, error_message)
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("BEGIN TRANSACTION")
        
        try:
            total = len(subscriptions)
            user_info = self._get_current_user_info()

            cursor = conn.cursor()

            # Precompute next protocol id base for this transaction to avoid collisions
            year = datetime.now().year
            year_short = str(year)[2:]
            
            # Check both new and old formats for backward compatibility
            cursor.execute(
                "SELECT protocol_id FROM subscriptions WHERE protocol_id LIKE ? ORDER BY protocol_id DESC LIMIT 1",
                (f"{year}-%",),
            )
            result_new = cursor.fetchone()
            
            cursor.execute(
                "SELECT protocol_id FROM subscriptions WHERE protocol_id LIKE ? ORDER BY protocol_id DESC LIMIT 1",
                (f"SUB-{year_short}-%",),
            )
            result_old = cursor.fetchone()
            
            # Get highest sequence number from both formats
            last_id = 0
            if result_new:
                last_id = max(last_id, int(result_new[0].split("-")[1]))
            if result_old:
                last_id = max(last_id, int(result_old[0].split("-")[2]))

            for idx, sub_data in enumerate(subscriptions):
                next_id = last_id + idx + 1
                protocol_id = f"{year}-{next_id:010d}"
                now = datetime.now().isoformat()
                
                # Encrypt sensitive fields
                email_encrypted = self.crypto.encrypt(sub_data.get("email", ""))
                address_encrypted = self.crypto.encrypt(sub_data.get("address", ""))
                mobile_encrypted = self.crypto.encrypt(sub_data.get("mobile", ""))
                payment_details_encrypted = self.crypto.encrypt(
                    str(sub_data["payment_details"])
                )
                
                # Insert subscription
                cursor.execute(
                    """INSERT INTO subscriptions 
                    (protocol_id, owner_name, license_plate, email_encrypted, 
                     address_encrypted, mobile_encrypted,
                     subscription_start, subscription_end, payment_details_encrypted, 
                     payment_method, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        protocol_id,
                        sub_data["owner_name"],
                        sub_data["license_plate"],
                        email_encrypted,
                        address_encrypted,
                        mobile_encrypted,
                        sub_data["subscription_start"].isoformat(),
                        sub_data["subscription_end"].isoformat(),
                        payment_details_encrypted,
                        sub_data["payment_method"],
                        now,
                        now,
                    ),
                )
                
                # Create HMAC signature
                # Get the row we just inserted
                cursor.execute(
                    "SELECT * FROM subscriptions WHERE protocol_id = ?", (protocol_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    columns = [
                        "protocol_id",
                        "owner_name",
                        "license_plate",
                        "email_encrypted",
                        "address_encrypted",
                        "mobile_encrypted",
                        "subscription_start",
                        "subscription_end",
                        "payment_details_encrypted",
                        "payment_method",
                        "created_at",
                        "updated_at",
                    ]
                    data = dict(zip(columns, row))
                    data["email_encrypted"] = base64.b64encode(
                        data["email_encrypted"]
                    ).decode("utf-8")
                    data["address_encrypted"] = base64.b64encode(
                        data["address_encrypted"]
                    ).decode("utf-8")
                    data["mobile_encrypted"] = base64.b64encode(
                        data["mobile_encrypted"]
                    ).decode("utf-8")
                    data["payment_details_encrypted"] = base64.b64encode(
                        data["payment_details_encrypted"]
                    ).decode("utf-8")
                    
                    signature = self.hmac.generate_hmac(data)
                    
                    cursor.execute(
                        """INSERT INTO data_integrity 
                        (table_name, record_id, signature, created_at) 
                        VALUES (?, ?, ?, ?)""",
                        (
                            "subscriptions",
                            protocol_id,
                            signature,
                            datetime.now().isoformat(),
                        ),
                    )
                
                # Add audit log entry
                subscription_data = {
                    "protocol_id": protocol_id,
                    "owner_name": sub_data["owner_name"],
                    "license_plate": sub_data["license_plate"],
                    "email": sub_data.get("email", ""),
                    "address": sub_data.get("address", ""),
                    "mobile": sub_data.get("mobile", ""),
                    "subscription_start": sub_data["subscription_start"].isoformat(),
                    "subscription_end": sub_data["subscription_end"].isoformat(),
                    "payment_details": sub_data["payment_details"],
                    "payment_method": sub_data["payment_method"],
                    "created_at": now,
                    "updated_at": now,
                }
                
                cursor.execute(
                    """INSERT INTO audit_log 
                    (operation_type, protocol_id, user, reason, before_data, after_data, ip_address, computer_name, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        "INSERT",
                        protocol_id,
                        user_info["user"],
                        reason,
                        None,
                        json.dumps(subscription_data, ensure_ascii=False),
                        user_info["ip_address"],
                        user_info["computer_name"],
                        now,
                    ),
                )
                
                # Update progress
                if progress_callback:
                    progress_callback(idx + 1, total)
            
            conn.commit()
            conn.close()
            return True, ""
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

    def perform_secure_backup(
        self,
        output_dir: Path,
        passphrase: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Create an encrypted backup of the database and keys.
        
        Steps:
        1. VACUUM INTO a temporary database snapshot
        2. Zip the database + crypto/HMAC keys (exclude configs)
        3. Encrypt with PBKDF2-derived key from passphrase
        4. Save as .enc file with metadata
        5. Clean up temporary files
        
        Args:
            output_dir: Directory to save backup file
            passphrase: User passphrase (minimum 16 characters)
            progress_callback: Optional callback(step, total_steps, message)
            
        Returns:
            Tuple of (success, message_or_error)
        """
        temp_db = None
        temp_zip = None
        
        try:
            # Step 1: Derive encryption key
            if progress_callback:
                progress_callback(1, 6, "Generazione chiave di cifratura...")
            
            key, salt = derive_key_from_passphrase(passphrase)
            
            # Step 2: Create safe SQLite snapshot
            if progress_callback:
                progress_callback(2, 6, "Creazione snapshot database...")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_db = Path(tempfile.gettempdir()) / f"temp_backup_{timestamp}.db"
            
            conn = sqlite3.connect(self.db_path)
            conn.execute(f"VACUUM INTO '{temp_db}'")
            conn.close()
            
            # Step 3: Create zip with DB + keys
            if progress_callback:
                progress_callback(3, 6, "Compressione database e chiavi...")
            
            temp_zip = Path(tempfile.gettempdir()) / f"temp_backup_{timestamp}.zip"
            
            with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add database
                zipf.write(temp_db, "database.db")
                
                # Add only crypto and HMAC keys (exclude RSA keys, configs, logs)
                keys_dir = self.db_path.parent / "keys"
                fernet_key = keys_dir / "fernet_key.bin"
                hmac_key = keys_dir / "hmac_key.bin"
                
                if fernet_key.exists():
                    zipf.write(fernet_key, "keys/fernet_key.bin")
                if hmac_key.exists():
                    zipf.write(hmac_key, "keys/hmac_key.bin")
            
            # Step 4: Encrypt the archive
            if progress_callback:
                progress_callback(4, 6, "Cifratura backup...")
            
            with open(temp_zip, 'rb') as f:
                archive_data = f.read()
            
            encrypted_data = encrypt_with_key(archive_data, key)
            
            # Step 5: Write encrypted file with metadata
            if progress_callback:
                progress_callback(5, 6, "Salvataggio backup cifrato...")
            
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            backup_filename = f"scalea_backup_{timestamp}.enc"
            backup_path = output_dir / backup_filename
            
            # Write metadata header + encrypted data
            with open(backup_path, 'wb') as f:
                # Header: magic(5) + version(1) + salt(32) + encrypted_data
                f.write(_BACKUP_MAGIC_HEADER)
                f.write(b'\x01')  # Version 1
                f.write(salt)
                f.write(encrypted_data)
            
            # Step 6: Cleanup
            if progress_callback:
                progress_callback(6, 6, "Pulizia file temporanei...")
            
            if temp_db and temp_db.exists():
                temp_db.unlink()
            if temp_zip and temp_zip.exists():
                temp_zip.unlink()
            
            return True, str(backup_path)
            
        except ValueError as e:
            # Passphrase validation error
            if temp_db and temp_db.exists():
                temp_db.unlink()
            if temp_zip and temp_zip.exists():
                temp_zip.unlink()
            return False, str(e)
            
        except Exception as e:
            # Other errors
            if temp_db and temp_db.exists():
                temp_db.unlink()
            if temp_zip and temp_zip.exists():
                temp_zip.unlink()
            return False, f"Errore durante il backup: {str(e)}"

    def restore_secure_backup(
        self,
        backup_path: Path,
        passphrase: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Restore database and keys from an encrypted backup.
        
        CAUTION: This will replace the current database and keys!
        
        Steps:
        1. Read encrypted backup file and extract salt
        2. Derive decryption key from passphrase
        3. Decrypt the archive
        4. Extract database and keys to temporary location
        5. Replace current database and keys atomically
        
        Args:
            backup_path: Path to .enc backup file
            passphrase: User passphrase used during backup
            progress_callback: Optional callback(step, total_steps, message)
            
        Returns:
            Tuple of (success, message_or_error)
        """
        temp_dir = None
        
        try:
            backup_path = Path(backup_path)
            
            if not backup_path.exists():
                return False, "File di backup non trovato"
            
            # Step 1: Read backup file
            if progress_callback:
                progress_callback(1, 5, "Lettura backup cifrato...")
            
            with open(backup_path, 'rb') as f:
                # Read and validate magic header
                magic = f.read(5)
                if magic != _BACKUP_MAGIC_HEADER:
                    return False, "File non valido: non è un backup di AbbonaMunicipale"
                
                version = f.read(1)
                if version != b'\x01':
                    return False, "Versione backup non supportata"
                
                salt = f.read(32)
                encrypted_data = f.read()
            
            # Step 2: Derive key
            if progress_callback:
                progress_callback(2, 5, "Derivazione chiave di cifratura...")
            
            key, _ = derive_key_from_passphrase(passphrase, salt)
            
            # Step 3: Decrypt
            if progress_callback:
                progress_callback(3, 5, "Decifratura backup...")
            
            try:
                archive_data = decrypt_with_key(encrypted_data, key)
            except Exception:
                return False, "Passphrase non corretta o backup danneggiato"
            
            # Step 4: Extract to temp
            if progress_callback:
                progress_callback(4, 5, "Estrazione database e chiavi...")
            
            temp_dir = Path(tempfile.mkdtemp())
            temp_zip = temp_dir / "backup.zip"
            
            with open(temp_zip, 'wb') as f:
                f.write(archive_data)
            
            with zipfile.ZipFile(temp_zip, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Step 5: Replace current files atomically
            if progress_callback:
                progress_callback(5, 5, "Ripristino database e chiavi...")
            
            # Create backup of current files
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup_dir = self.db_path.parent / f"pre_restore_backup_{timestamp}"
            current_backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup current database
            if self.db_path.exists():
                shutil.copy2(self.db_path, current_backup_dir / "database.db")
            
            # Backup current keys
            keys_dir = self.db_path.parent / "keys"
            if keys_dir.exists():
                shutil.copytree(keys_dir, current_backup_dir / "keys", dirs_exist_ok=True)
            
            try:
                # Replace database
                restored_db = temp_dir / "database.db"
                if restored_db.exists():
                    shutil.copy2(restored_db, self.db_path)
                else:
                    return False, "Database non trovato nel backup"
                
                # Replace keys
                restored_keys = temp_dir / "keys"
                if restored_keys.exists():
                    # Ensure keys directory exists
                    keys_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy each key file
                    for key_file in restored_keys.iterdir():
                        if key_file.is_file():
                            shutil.copy2(key_file, keys_dir / key_file.name)
                
                # Reinitialize crypto managers with restored keys
                self.crypto = CryptoManager(keys_dir)
                self.hmac = HMACManager(keys_dir)
                
                # Cleanup temp
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                return True, f"Backup ripristinato con successo. Backup precedente salvato in:\n{current_backup_dir}"
                
            except Exception as e:
                # Restore failed, rollback to current backup
                if current_backup_dir.exists():
                    if (current_backup_dir / "database.db").exists():
                        shutil.copy2(current_backup_dir / "database.db", self.db_path)
                    if (current_backup_dir / "keys").exists():
                        shutil.rmtree(keys_dir, ignore_errors=True)
                        shutil.copytree(current_backup_dir / "keys", keys_dir)
                
                return False, f"Errore durante il ripristino (rollback eseguito): {str(e)}"
            
        except ValueError as e:
            # Passphrase validation error
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            return False, str(e)
            
        except Exception as e:
            # Other errors
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            return False, f"Errore durante il ripristino: {str(e)}"