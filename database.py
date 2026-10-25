import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

from config import DB_PATH, HOLD_TTL_SECONDS

STATUS_HELD = "held"
STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_REJECTED = "rejected"
STATUS_CANCELLED = "cancelled"
STATUS_EXPIRED = "expired"

ACTIVE_STATUSES = (STATUS_HELD, STATUS_PENDING, STATUS_CONFIRMED)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def init_db() -> None:
    with closing(_connect()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL DEFAULT '',
                service_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                date_id TEXT NOT NULL,
                date_label TEXT NOT NULL,
                time_id TEXT NOT NULL,
                time_label TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'held'
                    CHECK (status IN ('held', 'pending', 'confirmed', 'rejected', 'cancelled', 'expired')),
                expires_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_bookings_active_slot
            ON bookings (date_id, time_id)
            WHERE status IN ('held', 'pending', 'confirmed')
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings (user_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings (status)"
        )
    expire_stale_holds()


def _expire_stale_holds(connection: sqlite3.Connection, now_text: str) -> None:
    connection.execute(
        """
        UPDATE bookings
        SET status = ?, updated_at = ?
        WHERE status = ? AND expires_at IS NOT NULL AND expires_at <= ?
        """,
        (STATUS_EXPIRED, now_text, STATUS_HELD, now_text),
    )


def expire_stale_holds() -> None:
    with closing(_connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            now_text = _format_utc(_now_utc())
            _expire_stale_holds(connection, now_text)
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise


def create_hold(
    user_id: int,
    username: str,
    service: dict,
    slot_date: dict,
    slot_time: dict,
    ttl_seconds: int | None = None,
) -> dict | None:
    ttl = ttl_seconds if ttl_seconds is not None else HOLD_TTL_SECONDS

    with closing(_connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            now = _now_utc()
            now_text = _format_utc(now)
            expires_text = _format_utc(now + timedelta(seconds=ttl))
            _expire_stale_holds(connection, now_text)
            connection.execute(
                """
                UPDATE bookings
                SET status = ?, updated_at = ?
                WHERE user_id = ? AND status = ?
                """,
                (STATUS_CANCELLED, now_text, user_id, STATUS_HELD),
            )
            cursor = connection.execute(
                """
                INSERT INTO bookings
                    (user_id, username, service_id, service_name,
                     date_id, date_label, time_id, time_label,
                     status, expires_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    service["id"],
                    service["name"],
                    slot_date["id"],
                    slot_date["label"],
                    slot_time["id"],
                    slot_time["label"],
                    STATUS_HELD,
                    expires_text,
                    now_text,
                    now_text,
                ),
            )
            booking_id = int(cursor.lastrowid)
            row = connection.execute(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,),
            ).fetchone()
            connection.execute("COMMIT")
            return dict(row) if row is not None else None
        except sqlite3.IntegrityError:
            connection.execute("ROLLBACK")
            return None
        except Exception:
            connection.execute("ROLLBACK")
            raise


def release_hold(booking_id: int, user_id: int) -> bool:
    with closing(_connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            now_text = _format_utc(_now_utc())
            cursor = connection.execute(
                """
                UPDATE bookings
                SET status = ?, updated_at = ?
                WHERE id = ? AND user_id = ? AND status = ?
                """,
                (STATUS_CANCELLED, now_text, booking_id, user_id, STATUS_HELD),
            )
            connection.execute("COMMIT")
            return cursor.rowcount > 0
        except Exception:
            connection.execute("ROLLBACK")
            raise


def release_user_holds(user_id: int) -> int:
    with closing(_connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            now_text = _format_utc(_now_utc())
            cursor = connection.execute(
                """
                UPDATE bookings
                SET status = ?, updated_at = ?
                WHERE user_id = ? AND status = ?
                """,
                (STATUS_CANCELLED, now_text, user_id, STATUS_HELD),
            )
            connection.execute("COMMIT")
            return cursor.rowcount
        except Exception:
            connection.execute("ROLLBACK")
            raise


def submit_hold(booking_id: int, user_id: int) -> dict | None:
    with closing(_connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            now_text = _format_utc(_now_utc())
            _expire_stale_holds(connection, now_text)
            row = connection.execute(
                """
                SELECT * FROM bookings
                WHERE id = ? AND user_id = ? AND status = ?
                """,
                (booking_id, user_id, STATUS_HELD),
            ).fetchone()
            if row is None:
                connection.execute("COMMIT")
                return None
            connection.execute(
                """
                UPDATE bookings
                SET status = ?, expires_at = NULL, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (STATUS_PENDING, now_text, booking_id, STATUS_HELD),
            )
            row = connection.execute(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,),
            ).fetchone()
            connection.execute("COMMIT")
            return dict(row) if row is not None else None
        except Exception:
            connection.execute("ROLLBACK")
            raise


def get_booking(booking_id: int) -> dict | None:
    expire_stale_holds()
    with closing(_connect()) as connection:
        row = connection.execute(
            "SELECT * FROM bookings WHERE id = ?",
            (booking_id,),
        ).fetchone()
        return dict(row) if row is not None else None


def get_occupied_time_ids(date_id: str) -> set[str]:
    expire_stale_holds()
    with closing(_connect()) as connection:
        rows = connection.execute(
            """
            SELECT time_id FROM bookings
            WHERE date_id = ? AND status IN (?, ?, ?)
            """,
            (date_id, STATUS_HELD, STATUS_PENDING, STATUS_CONFIRMED),
        ).fetchall()
        return {row["time_id"] for row in rows}


def get_user_bookings(user_id: int, limit: int = 20) -> list[dict]:
    expire_stale_holds()
    with closing(_connect()) as connection:
        rows = connection.execute(
            """
            SELECT * FROM bookings
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def get_pending_bookings(limit: int = 50) -> list[dict]:
    expire_stale_holds()
    with closing(_connect()) as connection:
        rows = connection.execute(
            """
            SELECT * FROM bookings
            WHERE status = ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (STATUS_PENDING, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def confirm_booking(booking_id: int) -> bool:
    with closing(_connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            now_text = _format_utc(_now_utc())
            cursor = connection.execute(
                """
                UPDATE bookings
                SET status = ?, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (STATUS_CONFIRMED, now_text, booking_id, STATUS_PENDING),
            )
            connection.execute("COMMIT")
            return cursor.rowcount > 0
        except Exception:
            connection.execute("ROLLBACK")
            raise


def reject_booking(booking_id: int) -> bool:
    with closing(_connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            now_text = _format_utc(_now_utc())
            cursor = connection.execute(
                """
                UPDATE bookings
                SET status = ?, expires_at = NULL, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (STATUS_REJECTED, now_text, booking_id, STATUS_PENDING),
            )
            connection.execute("COMMIT")
            return cursor.rowcount > 0
        except Exception:
            connection.execute("ROLLBACK")
            raise
