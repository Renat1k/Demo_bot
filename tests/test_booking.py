import os
import sqlite3
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

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

    def test_two_clients_cannot_hold_same_slot(self) -> None:
        def attempt(user_id: int):
            return self._hold(user_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, (1, 2)))

        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertIn("t1", database.get_occupied_time_ids("2026-10-27"))

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
