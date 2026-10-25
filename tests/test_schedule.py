from datetime import date, datetime, timezone
import unittest

import schedule


SERVICE_60 = {"id": "haircut", "duration_minutes": 60}
SERVICE_120 = {"id": "color", "duration_minutes": 120}


class ScheduleTests(unittest.TestCase):
    def test_clock_and_legacy_ids(self) -> None:
        self.assertEqual(schedule.parse_clock("09:30"), 570)
        self.assertIsNone(schedule.parse_clock("25:00"))
        self.assertEqual(schedule.time_to_minutes("t1"), 600)
        self.assertEqual(schedule.time_to_minutes("10:00"), 600)
        self.assertIsNone(schedule.time_to_minutes("unknown"))

    def test_break_and_future_slots(self) -> None:
        now = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)
        slots = [
            slot_id
            for slot_id, _label in schedule.available_slots(
                "2026-10-27", SERVICE_60, [], now=now
            )
        ]
        self.assertIn("09:00", slots)
        self.assertIn("11:00", slots)
        self.assertIn("14:00", slots)
        self.assertNotIn("12:30", slots)
        self.assertNotIn("13:00", slots)

    def test_duration_must_fit_before_break(self) -> None:
        now = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)
        slots = {
            slot_id
            for slot_id, _label in schedule.available_slots(
                "2026-10-27", SERVICE_120, [], now=now
            )
        }
        self.assertIn("11:00", slots)
        self.assertNotIn("11:30", slots)
        self.assertNotIn("12:00", slots)
        self.assertIn("14:00", slots)

    def test_occupied_interval_blocks_overlapping_starts(self) -> None:
        now = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)
        slots = {
            slot_id
            for slot_id, _label in schedule.available_slots(
                "2026-10-27",
                SERVICE_60,
                [(600, 660)],
                now=now,
            )
        }
        self.assertIn("09:00", slots)
        self.assertNotIn("09:30", slots)
        self.assertNotIn("10:00", slots)
        self.assertNotIn("10:30", slots)
        self.assertIn("11:00", slots)

    def test_date_labels_and_availability(self) -> None:
        now = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)
        dates = schedule.available_dates(
            SERVICE_60,
            today=date(2026, 10, 26),
            now=now,
            days=3,
        )
        self.assertEqual(dates[0], ("2026-10-26", "26 жовтня"))
        self.assertIn(("2026-10-27", "27 жовтня"), dates)
        self.assertEqual(schedule.date_label("2026-10-27"), "27 жовтня")

    def test_cancellation_window(self) -> None:
        booking = {
            "status": "pending",
            "date_id": "2026-10-27",
            "time_id": "10:00",
        }
        self.assertTrue(
            schedule.can_cancel(
                booking,
                now=datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc),
            )
        )
        self.assertFalse(
            schedule.can_cancel(
                booking,
                now=datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc),
            )
        )
        self.assertFalse(schedule.can_cancel({**booking, "status": "rejected"}))

    def test_booking_window(self) -> None:
        now = datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc)
        self.assertTrue(schedule.is_within_booking_window("2026-10-27", now=now))
        self.assertFalse(schedule.is_within_booking_window("2026-10-24", now=now))
        self.assertFalse(schedule.is_within_booking_window("2027-01-01", now=now))
        self.assertFalse(schedule.is_within_booking_window("bad-date", now=now))

    def test_slot_grid_and_fit(self) -> None:
        labels = {label for label, _start in schedule.slot_grid("2026-10-27")}
        self.assertIn("09:00", labels)
        self.assertIn("13:00", labels)
        self.assertIn("19:30", labels)
        self.assertTrue(schedule.can_fit("2026-10-27", SERVICE_60, 9 * 60))
        self.assertFalse(schedule.can_fit("2026-10-27", SERVICE_60, 12 * 60 + 30))
        self.assertFalse(schedule.can_fit("2026-10-27", SERVICE_60, 19 * 60 + 30))
        self.assertFalse(schedule.can_fit("2026-10-27", SERVICE_120, 11 * 60 + 30))
        self.assertTrue(schedule.can_fit("2026-10-27", SERVICE_120, 11 * 60))


if __name__ == "__main__":
    unittest.main()
