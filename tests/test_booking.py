import os
import sqlite3
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import database


SERVICE = {"id": "haircut", "name": "Стрижка"}
SLOT_DATE = {"id": "2026-10-27", "label": "27 жовтня"}
SLOT_TIME_1 = {"id": "t1", "label": "10:00"}
SLOT_TIME_2 = {"id": "t2", "label": "12:00"}


class BookingDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        database.DB_PATH = os.path.join(self.tmp.name, "test.db")
        database.init_db()

    def tearDown(self) -> None:
        database.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    def _hold(self, user_id: int, slot_time: dict = SLOT_TIME_1, ttl: int = 300):
        return database.create_hold(
            user_id,
            f"user{user_id}",
            SERVICE,
            SLOT_DATE,
            slot_time,
            ttl_seconds=ttl,
        )

    def test_slot_is_exclusive_and_released(self) -> None:
        hold = self._hold(1)
        self.assertIsNotNone(hold)
        self.assertIsNone(self._hold(2))
        self.assertIn("t1", database.get_occupied_time_ids("2026-10-27"))

        self.assertTrue(database.release_hold(hold["id"], 1))
        self.assertNotIn("t1", database.get_occupied_time_ids("2026-10-27"))
        self.assertIsNotNone(self._hold(2))

    def test_submit_confirm_reject_and_repeated_actions(self) -> None:
        hold = self._hold(1)
        self.assertIsNotNone(hold)
        pending = database.submit_hold(hold["id"], 1)
        self.assertIsNotNone(pending)
        self.assertEqual(pending["status"], "pending")
        self.assertIsNone(pending["expires_at"])
        self.assertIn("t1", database.get_occupied_time_ids("2026-10-27"))
        self.assertIsNone(database.submit_hold(hold["id"], 1))

        self.assertTrue(database.confirm_booking(hold["id"]))
        self.assertEqual(database.get_booking(hold["id"])["status"], "confirmed")
        self.assertFalse(database.confirm_booking(hold["id"]))
        self.assertFalse(database.reject_booking(hold["id"]))
        self.assertIn("t1", database.get_occupied_time_ids("2026-10-27"))

    def test_reject_frees_slot(self) -> None:
        hold = self._hold(1, SLOT_TIME_2)
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        self.assertTrue(database.reject_booking(hold["id"]))
        self.assertEqual(database.get_booking(hold["id"])["status"], "rejected")
        self.assertFalse(database.reject_booking(hold["id"]))
        self.assertNotIn("t2", database.get_occupied_time_ids("2026-10-27"))
        self.assertIsNotNone(self._hold(2, SLOT_TIME_2))

    def test_hold_cannot_be_submitted_after_expiry(self) -> None:
        hold = self._hold(1, ttl=-1)
        self.assertIsNotNone(hold)
        self.assertIsNone(database.submit_hold(hold["id"], 1))
        self.assertEqual(database.get_booking(hold["id"])["status"], "expired")
        self.assertNotIn("t1", database.get_occupied_time_ids("2026-10-27"))
        self.assertIsNotNone(self._hold(2))
        self.assertIn("t1", database.get_occupied_time_ids("2026-10-27"))

    def test_overlapping_service_intervals_are_rejected(self) -> None:
        long_service = {**SERVICE, "duration_minutes": 60}
        first = database.create_hold(
            1,
            "one",
            long_service,
            SLOT_DATE,
            {"id": "10:00", "label": "10:00"},
        )
        self.assertIsNotNone(first)
        self.assertIsNone(
            database.create_hold(
                2,
                "two",
                long_service,
                SLOT_DATE,
                {"id": "10:30", "label": "10:30"},
            )
        )
        second = database.create_hold(
            2,
            "two",
            long_service,
            SLOT_DATE,
            {"id": "11:00", "label": "11:00"},
        )
        self.assertIsNotNone(second)
        self.assertEqual(
            database.get_occupied_intervals("2026-10-27"),
            [(600, 660), (660, 720)],
        )

    def test_old_schema_is_migrated(self) -> None:
        with closing(sqlite3.connect(database.DB_PATH)) as connection:
            connection.execute("DROP TABLE bookings")
            connection.execute(
                """
                CREATE TABLE bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL DEFAULT '',
                    service_id TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    date_id TEXT NOT NULL,
                    date_label TEXT NOT NULL,
                    time_id TEXT NOT NULL,
                    time_label TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'held',
                    expires_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

        database.init_db()
        with closing(sqlite3.connect(database.DB_PATH)) as connection:
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(bookings)").fetchall()
            }
        self.assertIn("duration_minutes", columns)
        self.assertIn("price_label", columns)
        self.assertIn("client_token", columns)

    def test_client_cancel_frees_slot_and_checks_owner(self) -> None:
        future_date = {"id": "2099-01-05", "label": "5 січня"}
        hold = database.create_hold(
            1,
            "one",
            SERVICE,
            future_date,
            {"id": "10:00", "label": "10:00"},
        )
        self.assertIsNotNone(hold)
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))

        self.assertIsNone(database.cancel_user_booking(hold["id"], 2))
        self.assertEqual(database.get_booking(hold["id"])["status"], "pending")

        updated = database.cancel_user_booking(hold["id"], 1)
        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "cancelled")
        self.assertNotIn("10:00", database.get_occupied_time_ids("2099-01-05"))
        self.assertIsNone(database.cancel_user_booking(hold["id"], 1))

    def test_confirmed_booking_can_be_cancelled_by_client(self) -> None:
        future_date = {"id": "2099-01-05", "label": "5 січня"}
        hold = database.create_hold(
            1,
            "one",
            SERVICE,
            future_date,
            {"id": "11:00", "label": "11:00"},
        )
        self.assertIsNotNone(hold)
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        self.assertTrue(database.confirm_booking(hold["id"]))
        updated = database.cancel_user_booking(hold["id"], 1)
        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "cancelled")
        self.assertNotIn("11:00", database.get_occupied_time_ids("2099-01-05"))

    def test_past_booking_cannot_be_cancelled_online(self) -> None:
        past_date = {"id": "2000-01-05", "label": "5 січня"}
        hold = database.create_hold(
            1,
            "one",
            SERVICE,
            past_date,
            {"id": "10:00", "label": "10:00"},
        )
        self.assertIsNotNone(hold)
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        self.assertIsNone(database.cancel_user_booking(hold["id"], 1))
        self.assertEqual(database.get_booking(hold["id"])["status"], "pending")

    def test_hold_idempotency_token_returns_same_row(self) -> None:
        first = database.create_hold(
            1,
            "one",
            SERVICE,
            SLOT_DATE,
            {"id": "10:00", "label": "10:00"},
            client_token="mini-app-hold-1",
        )
        second = database.create_hold(
            1,
            "one",
            SERVICE,
            SLOT_DATE,
            {"id": "10:00", "label": "10:00"},
            client_token="mini-app-hold-1",
        )
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first["id"], second["id"])

    def test_concurrent_same_idempotency_token_creates_one_hold(self) -> None:
        def attempt(_index: int):
            return database.create_hold(
                1,
                "one",
                SERVICE,
                SLOT_DATE,
                {"id": "10:00", "label": "10:00"},
                client_token="concurrent-token",
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, (1, 2)))

        self.assertTrue(all(result is not None for result in results))
        self.assertEqual(results[0]["id"], results[1]["id"])
        with closing(sqlite3.connect(database.DB_PATH)) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM bookings WHERE client_token = ?",
                ("concurrent-token",),
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_bookings_for_date_returns_active_only(self) -> None:
        active = database.create_hold(
            1,
            "one",
            SERVICE,
            SLOT_DATE,
            {"id": "10:00", "label": "10:00"},
        )
        rejected = database.create_hold(
            2,
            "two",
            SERVICE,
            SLOT_DATE,
            {"id": "11:00", "label": "11:00"},
        )
        self.assertIsNotNone(active)
        self.assertIsNotNone(rejected)
        database.submit_hold(rejected["id"], 2)
        database.reject_booking(rejected["id"])
        rows = database.get_bookings_for_date("2026-10-27")
        self.assertEqual([row["id"] for row in rows], [active["id"]])

    def test_two_clients_cannot_hold_same_slot(self) -> None:
        def attempt(user_id: int):
            return self._hold(user_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, (1, 2)))

        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertIn("t1", database.get_occupied_time_ids("2026-10-27"))

    def test_concurrent_overlapping_starts_have_one_winner(self) -> None:
        service = {**SERVICE, "duration_minutes": 60}

        def attempt(args: tuple[int, str]):
            user_id, time_id = args
            return database.create_hold(
                user_id,
                f"user{user_id}",
                service,
                SLOT_DATE,
                {"id": time_id, "label": time_id},
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ((1, "10:00"), (2, "10:30"))))

        self.assertEqual(sum(result is not None for result in results), 1)

    def test_submit_checks_expiry_after_waiting_for_lock(self) -> None:
        hold = self._hold(1, ttl=1)
        self.assertIsNotNone(hold)

        lock = sqlite3.connect(database.DB_PATH, timeout=10, isolation_level=None)
        lock.execute("PRAGMA journal_mode = WAL")
        lock.execute("BEGIN IMMEDIATE")
        result = {}

        def submit() -> None:
            result["booking"] = database.submit_hold(hold["id"], 1)

        worker = threading.Thread(target=submit)
        worker.start()
        try:
            time.sleep(1.2)
        finally:
            lock.execute("COMMIT")
            lock.close()

        worker.join(timeout=10)
        self.assertFalse(worker.is_alive())
        self.assertIsNone(result.get("booking"))
        self.assertEqual(database.get_booking(hold["id"])["status"], "expired")

    def test_restart_keeps_pending_and_expires_holds(self) -> None:
        pending_hold = self._hold(1)
        self.assertIsNotNone(database.submit_hold(pending_hold["id"], 1))
        expired_hold = self._hold(2, SLOT_TIME_2, ttl=-1)
        active_hold = self._hold(3, {"id": "t3", "label": "14:00"}, ttl=300)
        self.assertIsNotNone(expired_hold)
        self.assertIsNotNone(active_hold)

        database.init_db()

        self.assertEqual(database.get_booking(pending_hold["id"])["status"], "pending")
        self.assertEqual(database.get_booking(expired_hold["id"])["status"], "expired")
        self.assertEqual(database.get_booking(active_hold["id"])["status"], "held")
        self.assertIn("t1", database.get_occupied_time_ids("2026-10-27"))
        self.assertNotIn("t2", database.get_occupied_time_ids("2026-10-27"))
        self.assertIn("t3", database.get_occupied_time_ids("2026-10-27"))

    def test_release_user_holds_frees_slot(self) -> None:
        hold = self._hold(1)
        self.assertEqual(database.release_user_holds(1), 1)
        self.assertEqual(database.get_booking(hold["id"])["status"], "cancelled")
        self.assertNotIn("t1", database.get_occupied_time_ids("2026-10-27"))


if __name__ == "__main__":
    unittest.main()
