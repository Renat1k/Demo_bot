import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

from config import DB_PATH, HOLD_TTL_SECONDS
from schedule import can_cancel, overlaps, time_to_minutes

logger = logging.getLogger(__name__)

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


def _ensure_column(connection: sqlite3.Connection, name: str, definition: str) -> None:
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(bookings)").fetchall()
    }
    if name not in columns:
        connection.execute(f"ALTER TABLE bookings ADD COLUMN {name} {definition}")


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
                price_label TEXT NOT NULL DEFAULT '',
                duration_minutes INTEGER NOT NULL DEFAULT 60,
                date_id TEXT NOT NULL,
                date_label TEXT NOT NULL,
                time_id TEXT NOT NULL,
                time_label TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'held'
                    CHECK (status IN ('held', 'pending', 'confirmed', 'rejected', 'cancelled', 'expired')),
                expires_at TEXT,
                client_token TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_column(connection, "price_label", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "duration_minutes", "INTEGER NOT NULL DEFAULT 60")
        _ensure_column(connection, "client_token", "TEXT NOT NULL DEFAULT ''")
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_bookings_active_slot
            ON bookings (date_id, time_id)
            WHERE status IN ('held', 'pending', 'confirmed')
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_bookings_client_token ON bookings (client_token)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings (user_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings (status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_bookings_date_status ON bookings (date_id, status)"
        )
    expire_stale_holds()


def _expire_stale_holds(connection: sqlite3.Connection, now_text: str) -> int:
    cursor = connection.execute(
        """
        UPDATE bookings
        SET status = ?, updated_at = ?
        WHERE status = ? AND expires_at IS NOT NULL AND expires_at <= ?
        """,
        (STATUS_EXPIRED, now_text, STATUS_HELD, now_text),
    )
    return cursor.rowcount


def expire_stale_holds() -> None:
    with closing(_connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            now_text = _format_utc(_now_utc())
            expired = _expire_stale_holds(connection, now_text)
            connection.execute("COMMIT")
            if expired:
                logger.info("expired_holds count=%s", expired)
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
    client_token: str = "",
) -> dict | None:
    ttl = ttl_seconds if ttl_seconds is not None else HOLD_TTL_SECONDS
    token = (client_token or "").strip()[:80]

    with closing(_connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            now = _now_utc()
            now_text = _format_utc(now)
            expires_text = _format_utc(now + timedelta(seconds=ttl))
            duration = int(service.get("duration_minutes", 60))
            if duration <= 0:
                connection.execute("ROLLBACK")
                return None
            start_minutes = time_to_minutes(str(slot_time.get("id", "")))
            if start_minutes is None:
                connection.execute("ROLLBACK")
                return None
            _expire_stale_holds(connection, now_text)

            if token:
                previous = connection.execute(
                    """
                    SELECT * FROM bookings
                    WHERE client_token = ? AND user_id = ?
                    ORDER BY id DESC LIMIT 1
                    """,
                    (token, user_id),
                ).fetchone()
                if previous is not None:
                    connection.execute("COMMIT")
                    result = dict(previous)
                    result["idempotent"] = True
                    return result

            existing = connection.execute(
                """
                SELECT time_id, duration_minutes FROM bookings
                WHERE date_id = ? AND status IN (?, ?, ?)
                  AND NOT (user_id = ? AND status = ?)
                """,
                (
                    slot_date["id"],
                    STATUS_HELD,
                    STATUS_PENDING,
                    STATUS_CONFIRMED,
                    user_id,
                    STATUS_HELD,
                ),
            ).fetchall()
            for row in existing:
                existing_start = time_to_minutes(str(row["time_id"]))
                if existing_start is None:
                    continue
                existing_end = existing_start + int(row["duration_minutes"] or 60)
                if overlaps(start_minutes, start_minutes + duration, existing_start, existing_end):
                    connection.execute("ROLLBACK")
                    return None

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
                     price_label, duration_minutes,
                     date_id, date_label, time_id, time_label,
                     status, expires_at, client_token, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    service["id"],
                    service["name"],
                    str(service.get("price", "")),
                    duration,
                    slot_date["id"],
                    slot_date["label"],
                    slot_time["id"],
                    slot_time["label"],
                    STATUS_HELD,
                    expires_text,
                    token,
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
            logger.info(
                "hold_created id=%s user=%s date=%s time=%s duration=%s",
                booking_id,
                user_id,
                slot_date["id"],
                slot_time["id"],
                duration,
            )
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
            logger.info("hold_submitted id=%s user=%s", booking_id, user_id)
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


def get_occupied_intervals(date_id: str) -> list[tuple[int, int]]:
    expire_stale_holds()
    with closing(_connect()) as connection:
        rows = connection.execute(
            """
            SELECT time_id, duration_minutes FROM bookings
            WHERE date_id = ? AND status IN (?, ?, ?)
            ORDER BY time_id
            """,
            (date_id, STATUS_HELD, STATUS_PENDING, STATUS_CONFIRMED),
        ).fetchall()
    intervals: list[tuple[int, int]] = []
    for row in rows:
        start = time_to_minutes(str(row["time_id"]))
        if start is None:
            continue
        intervals.append((start, start + int(row["duration_minutes"] or 60)))
    return intervals


def get_bookings(
    status: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> list[dict]:
    expire_stale_holds()
    query = "SELECT * FROM bookings"
    params: list[object] = []
    if status is not None:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with closing(_connect()) as connection:
        rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def count_bookings(status: str | None = None) -> int:
    expire_stale_holds()
    query = "SELECT COUNT(*) AS total FROM bookings"
    params: list[object] = []
    if status is not None:
        query += " WHERE status = ?"
        params.append(status)
    with closing(_connect()) as connection:
        row = connection.execute(query, params).fetchone()
        return int(row["total"]) if row is not None else 0


def get_bookings_for_date(
    date_id: str,
    statuses: tuple[str, ...] = ACTIVE_STATUSES,
) -> list[dict]:
    expire_stale_holds()
    if not statuses:
        return []
    placeholders = ", ".join("?" for _ in statuses)
    query = (
        "SELECT * FROM bookings "
        f"WHERE date_id = ? AND status IN ({placeholders}) "
        "ORDER BY time_id, id"
    )
    with closing(_connect()) as connection:
        rows = connection.execute(
            query,
            (date_id, *statuses),
        ).fetchall()
        return [dict(row) for row in rows]


def cancel_user_booking(booking_id: int, user_id: int) -> dict | None:
    with closing(_connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            now = _now_utc()
            now_text = _format_utc(now)
            row = connection.execute(
                "SELECT * FROM bookings WHERE id = ? AND user_id = ?",
                (booking_id, user_id),
            ).fetchone()
            if row is None or row["status"] not in (STATUS_PENDING, STATUS_CONFIRMED):
                connection.execute("COMMIT")
                return None
            if not can_cancel(dict(row), now=now):
                connection.execute("COMMIT")
                return None
            connection.execute(
                """
                UPDATE bookings
                SET status = ?, expires_at = NULL, updated_at = ?
                WHERE id = ? AND user_id = ? AND status IN (?, ?)
                """,
                (
                    STATUS_CANCELLED,
                    now_text,
                    booking_id,
                    user_id,
                    STATUS_PENDING,
                    STATUS_CONFIRMED,
                ),
            )
            updated = connection.execute(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,),
            ).fetchone()
            connection.execute("COMMIT")
            logger.info("booking_cancelled id=%s user=%s", booking_id, user_id)
            return dict(updated) if updated is not None else None
        except Exception:
            connection.execute("ROLLBACK")
            raise


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
            if cursor.rowcount:
                logger.info("booking_confirmed id=%s", booking_id)
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
            if cursor.rowcount:
                logger.info("booking_rejected id=%s", booking_id)
            return cursor.rowcount > 0
        except Exception:
            connection.execute("ROLLBACK")
            raise
