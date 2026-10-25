import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from unittest import mock
from urllib.parse import urlencode

import config
import database
import schedule
import telegram_api

try:
    from web import app as flask_app
except ModuleNotFoundError:
    flask_app = None


def build_init_data(user_id: int = 1, username: str = "client") -> str:
    values = {
        "auth_date": str(int(time.time())),
        "query_id": "query-1",
        "user": json.dumps(
            {
                "id": user_id,
                "first_name": "Client",
                "username": username,
                "language_code": "uk",
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(
        b"WebAppData",
        config.BOT_TOKEN.encode(),
        hashlib.sha256,
    ).digest()
    values["hash"] = hmac.new(
        secret,
        check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)


@unittest.skipIf(flask_app is None, "Flask is not installed in this environment")
class MiniAppApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        self.old_bot_token = config.BOT_TOKEN
        self.old_admin_id = config.ADMIN_CHAT_ID
        self.old_webapp_url = config.WEBAPP_URL
        database.DB_PATH = os.path.join(self.tmp.name, "test.db")
        config.BOT_TOKEN = "123456:TEST-TOKEN"
        config.ADMIN_CHAT_ID = 999
        config.WEBAPP_URL = "https://example.test/app"
        database.init_db()
        self.client = flask_app.test_client()
        self.client_context = flask_app.app_context()
        self.client_context.push()
        self.notification_patch = mock.patch(
            "telegram_api.send_message",
            return_value=True,
        )
        self.send_message = self.notification_patch.start()

    def tearDown(self) -> None:
        self.notification_patch.stop()
        self.client_context.pop()
        database.DB_PATH = self.old_db_path
        config.BOT_TOKEN = self.old_bot_token
        config.ADMIN_CHAT_ID = self.old_admin_id
        config.WEBAPP_URL = self.old_webapp_url
        self.tmp.cleanup()

    def _headers(self, user_id: int = 1) -> dict:
        return {"X-Telegram-Init-Data": build_init_data(user_id)}

    def _slot(self, service_id: str = "haircut") -> tuple[str, str, dict]:
        service = config.SERVICES_BY_ID[service_id]
        dates = schedule.available_dates(
            service,
            occupied_lookup=database.get_occupied_intervals,
        )
        self.assertTrue(dates, "test schedule has no bookable dates")
        date_id = dates[0][0]
        slots = schedule.available_slots(
            date_id,
            service,
            database.get_occupied_intervals(date_id),
        )
        self.assertTrue(slots, "test schedule has no bookable slots")
        return date_id, slots[0][0], service

    def _create_hold(self, user_id: int = 1, time_id: str | None = None, date_id: str | None = None):
        if date_id is None or time_id is None:
            selected_date, selected_time, _ = self._slot()
            date_id = date_id or selected_date
            time_id = time_id or selected_time
        service = config.SERVICES_BY_ID["haircut"]
        hold = database.create_hold(
            user_id,
            "client",
            service,
            {"id": date_id, "label": schedule.date_label(date_id)},
            {"id": time_id, "label": time_id},
        )
        self.assertIsNotNone(hold)
        return hold

    def test_health_and_static_app(self) -> None:
        self.assertEqual(self.client.get("/health").status_code, 200)
        root = self.client.get("/")
        self.assertEqual(root.status_code, 200)
        self.assertIn(b"DEMO", root.data)
        self.assertIn("Content-Security-Policy", root.headers)
        root.close()
        response = self.client.get("/app")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"DEMO", response.data)
        self.assertIn("Content-Security-Policy", response.headers)
        response.close()
        asset = self.client.get("/app/app.js")
        self.assertEqual(asset.status_code, 200)
        asset.close()

    def test_config_requires_valid_init_data(self) -> None:
        self.assertEqual(self.client.get("/api/config").status_code, 401)
        self.assertEqual(
            self.client.get("/api/config", headers={"X-Telegram-Init-Data": "broken"}).status_code,
            401,
        )
        response = self.client.get("/api/config", headers=self._headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["salon"]["name"], "DEMO")

    def test_tampered_init_data_is_rejected(self) -> None:
        data = build_init_data(1).replace("Client", "Hacker")
        response = self.client.get(
            "/api/config",
            headers={"X-Telegram-Init-Data": data},
        )
        self.assertEqual(response.status_code, 401)

    def test_bot_hold_is_visible_in_miniapp_availability(self) -> None:
        date_id, time_id, _service = self._slot()
        hold = self._create_hold(date_id=date_id, time_id=time_id)
        self.assertIsNotNone(hold)
        response = self.client.get(
            f"/api/availability?service_id=haircut&date={date_id}",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        slot = next(item for item in response.json["data"]["slots"] if item["id"] == time_id)
        self.assertEqual(slot["status"], "booked")

        submitted = self.client.post(
            f"/api/holds/{hold['id']}/submit",
            headers=self._headers(),
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json["data"]["booking"]["status"], "pending")

    def test_api_hold_submit_admin_confirm_and_idempotency(self) -> None:
        date_id, time_id, _service = self._slot()
        headers = self._headers()
        payload = {"service_id": "haircut", "date": date_id, "time": time_id}
        first = self.client.post(
            "/api/holds",
            json=payload,
            headers={**headers, "Idempotency-Key": "retry-key-1"},
        )
        self.assertEqual(first.status_code, 200)
        hold_id = first.json["data"]["booking"]["id"]
        repeat = self.client.post(
            "/api/holds",
            json=payload,
            headers={**headers, "Idempotency-Key": "retry-key-1"},
        )
        self.assertEqual(repeat.status_code, 200)
        self.assertEqual(repeat.json["data"]["booking"]["id"], hold_id)

        submitted = self.client.post(
            f"/api/holds/{hold_id}/submit",
            headers=headers,
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json["data"]["booking"]["status"], "pending")
        duplicate = self.client.post(
            f"/api/holds/{hold_id}/submit",
            headers=headers,
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json["data"]["booking"]["status"], "pending")

        admin_headers = self._headers(999)
        pending = self.client.get(
            "/api/admin/bookings?status=pending",
            headers=admin_headers,
        )
        self.assertEqual(pending.status_code, 200)
        self.assertTrue(any(item["id"] == hold_id for item in pending.json["data"]["items"]))
        confirmed = self.client.post(
            f"/api/admin/bookings/{hold_id}/confirm",
            headers=admin_headers,
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json["data"]["booking"]["status"], "confirmed")
        self.assertEqual(database.get_booking(hold_id)["status"], "confirmed")

    def test_non_admin_cannot_use_admin_api(self) -> None:
        response = self.client.get(
            "/api/admin/bookings?status=pending",
            headers=self._headers(2),
        )
        self.assertEqual(response.status_code, 403)

    def test_client_cancel_frees_slot(self) -> None:
        hold = database.create_hold(
            1,
            "client",
            config.SERVICES_BY_ID["haircut"],
            {"id": "2099-01-05", "label": "5 січня"},
            {"id": "10:00", "label": "10:00"},
        )
        self.assertIsNotNone(hold)
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        response = self.client.delete(
            f"/api/bookings/{hold['id']}",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["booking"]["status"], "cancelled")
        self.assertNotIn(
            hold["time_id"],
            database.get_occupied_time_ids(hold["date_id"]),
        )

    def test_foreign_booking_is_not_visible(self) -> None:
        hold = self._create_hold()
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        response = self.client.get(
            f"/api/bookings/{hold['id']}",
            headers=self._headers(2),
        )
        self.assertEqual(response.status_code, 404)

    def test_expired_hold_submit_returns_conflict(self) -> None:
        date_id, time_id, service = self._slot()
        hold = database.create_hold(
            1,
            "client",
            service,
            {"id": date_id, "label": schedule.date_label(date_id)},
            {"id": time_id, "label": time_id},
            ttl_seconds=-1,
        )
        self.assertIsNotNone(hold)
        response = self.client.post(
            f"/api/holds/{hold['id']}/submit",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"]["code"], "hold_expired")

    def test_invalid_parameters_return_safe_errors(self) -> None:
        response = self.client.post(
            "/api/holds",
            json={"service_id": "missing", "date": "bad", "time": "99:99"},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Traceback", response.get_data(as_text=True))
        response = self.client.get(
            "/api/availability?service_id=missing",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_pagination(self) -> None:
        date_id = "2099-01-05"
        for index in range(11):
            time_id = f"{9 + index:02d}:00"
            hold = database.create_hold(
                1,
                "client",
                config.SERVICES_BY_ID["haircut"],
                {"id": date_id, "label": "5 січня"},
                {"id": time_id, "label": time_id},
            )
            self.assertIsNotNone(hold)
            self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        response = self.client.get(
            "/api/admin/bookings?status=pending&page=2",
            headers=self._headers(999),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["pages"], 2)
        self.assertEqual(len(response.json["data"]["items"]), 1)

    def test_admin_day_lists_active_bookings(self) -> None:
        hold = self._create_hold()
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        response = self.client.get(
            f"/api/admin/day?date={hold['date_id']}",
            headers=self._headers(999),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item["id"] == hold["id"] for item in response.json["data"]["bookings"]))


if __name__ == "__main__":
    unittest.main()
