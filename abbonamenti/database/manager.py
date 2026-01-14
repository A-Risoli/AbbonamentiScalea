import base64

import json
import os
import socket
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from abbonamenti.database.schema import AuditLogEntry, Schema, Subscription
from abbonamenti.security.crypto import CryptoManager
from abbonamenti.security.hmac import HMACManager


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
        cursor.execute(
            "SELECT protocol_id FROM subscriptions WHERE protocol_id LIKE ? ORDER BY protocol_id DESC LIMIT 1",
            (f"SUB-{year_short}%",),
        )
        result = cursor.fetchone()
        conn.close()

        if result:
            last_id = int(result[0].split("-")[-1])
            new_id = last_id + 1
        else:
            new_id = 1

        return f"SUB-{year_short}-{new_id:04d}"

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

    def _get_subscriptions_for_stats(self) -> list[dict]:
        """
        Lightweight query for statistics - only decrypts payment_details.
        Returns dict with minimal fields needed for analytics.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """SELECT protocol_id, subscription_start, subscription_end,
                      payment_details_encrypted, payment_method
               FROM subscriptions ORDER BY protocol_id"""
        )
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

    def get_all_subscriptions(self) -> list[Subscription]:
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

    def search_subscriptions(self, query: str) -> list[Subscription]:
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
    ) -> list[AuditLogEntry]:
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

    def verify_data_integrity(self) -> tuple[bool, list[str]]:
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
        self, year: int | None = None, month: int | None = None
    ) -> dict:
        """Get payment statistics for a given year and/or month"""
        # Use lightweight query for performance
        subs = self._get_subscriptions_for_stats()
        
        # Filter by year and month
        filtered_subs = []
        for sub in subs:
            if year and sub["subscription_start"].year != year:
                continue
            if month and sub["subscription_start"].month != month:
                continue
            filtered_subs.append(sub)

        # Calculate statistics
        total_revenue = sum(sub["payment_details"] for sub in filtered_subs)
        subscription_count = len(filtered_subs)
        average_payment = total_revenue / subscription_count if subscription_count > 0 else 0.0
        
        pos_count = sum(1 for sub in filtered_subs if sub["payment_method"] == "POS")
        bollettino_count = sum(1 for sub in filtered_subs if sub["payment_method"] == "Bollettino")

        return {
            "total_revenue": total_revenue,
            "subscription_count": subscription_count,
            "average_payment": average_payment,
            "pos_count": pos_count,
            "bollettino_count": bollettino_count,
        }

    def get_monthly_revenue(self, year: int | None = None, month: int | None = None) -> list[tuple[str, float]]:
        """Get revenue grouped by month, respecting optional year/month filters"""
        subs = self._get_subscriptions_for_stats()

        # Filter by year and month if specified
        if year:
            subs = [sub for sub in subs if sub["subscription_start"].year == year]
        if month:
            subs = [sub for sub in subs if sub["subscription_start"].month == month]

        # Group by month (or single month if filtered)
        monthly: dict[str, float] = {}
        for sub in subs:
            month_label = sub["subscription_start"].strftime("%b %Y")
            if month_label not in monthly:
                monthly[month_label] = 0.0
            monthly[month_label] += sub["payment_details"]

        # Sort by date label
        return sorted(monthly.items(), key=lambda x: x[0])

    def get_payment_methods_breakdown(
        self, year: int | None = None, month: int | None = None
    ) -> dict[str, int]:
        """Get count of subscriptions by payment method"""
        subs = self._get_subscriptions_for_stats()

        # Filter by year and month
        if year:
            subs = [sub for sub in subs if sub["subscription_start"].year == year]
        if month:
            subs = [sub for sub in subs if sub["subscription_start"].month == month]

        methods = {"POS": 0, "Bollettino": 0}
        for sub in subs:
            if sub["payment_method"] in methods:
                methods[sub["payment_method"]] += 1

        return methods

    def get_revenue_trend(self, year: int | None = None, month: int | None = None) -> list[tuple[str, float]]:
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
        trend: list[tuple[str, float]] = []
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

    def get_subscriptions_per_month(self, year: int | None = None, month: int | None = None) -> list[tuple[str, int]]:
        """Get count of subscriptions created per month, respecting filters"""
        subs = self._get_subscriptions_for_stats()

        # Filter by year/month if specified
        if year:
            subs = [sub for sub in subs if sub["subscription_start"].year == year]
        if month:
            subs = [sub for sub in subs if sub["subscription_start"].month == month]

        # Group by month
        monthly: dict[str, int] = {}
        for sub in subs:
            month_label = sub["subscription_start"].strftime("%b %Y")
            if month_label not in monthly:
                monthly[month_label] = 0
            monthly[month_label] += 1

        # Sort by date label
        return sorted(monthly.items(), key=lambda x: x[0])
