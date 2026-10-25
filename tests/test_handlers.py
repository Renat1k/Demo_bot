import os
import re
import sys
import tempfile
import types
import unittest

telegram = types.ModuleType("telegram")


class InlineKeyboardButton:
    def __init__(self, text, callback_data=None, **kwargs):
        self.text = text
        self.callback_data = callback_data


class InlineKeyboardMarkup:
    def __init__(self, inline_keyboard, **kwargs):
        self.inline_keyboard = inline_keyboard


class CallbackQuery:
    pass


class Update:
    pass


telegram.InlineKeyboardButton = InlineKeyboardButton
telegram.InlineKeyboardMarkup = InlineKeyboardMarkup
telegram.CallbackQuery = CallbackQuery
telegram.Update = Update
sys.modules["telegram"] = telegram

constants = types.ModuleType("telegram.constants")


class ParseMode:
    HTML = "HTML"


constants.ParseMode = ParseMode
sys.modules["telegram.constants"] = constants

errors = types.ModuleType("telegram.error")


class BadRequest(Exception):
    pass


class TelegramError(Exception):
    pass


errors.BadRequest = BadRequest
errors.TelegramError = TelegramError
sys.modules["telegram.error"] = errors

ext = types.ModuleType("telegram.ext")


class ContextTypes:
    DEFAULT_TYPE = object


class Application:
    pass


class CallbackQueryHandler:
    def __init__(self, callback, pattern=None, **kwargs):
        self.callback = callback
        self.pattern = pattern


class CommandHandler:
    def __init__(self, command, callback, **kwargs):
        self.command = command
        self.callback = callback


ext.ContextTypes = ContextTypes
ext.Application = Application
ext.CallbackQueryHandler = CallbackQueryHandler
ext.CommandHandler = CommandHandler
telegram.ext = ext
sys.modules["telegram.ext"] = ext

import config
import database
import keyboards
import notifications
import schedule
import texts
from handlers import admin, common, user, register_handlers


SERVICE = {"id": "haircut", "name": "Стрижка"}
SLOT_DATE = {"id": "2026-10-27", "label": "27 жовтня"}
SLOT_TIME = {"id": "t1", "label": "10:00"}


class FakeUser:
    def __init__(self, user_id: int, username: str = "client") -> None:
        self.id = user_id
        self.username = username


class FakeQuery:
    def __init__(self, data: str) -> None:
        self.data = data
        self.answers = []
        self.edits = []
        self.markups = []

    async def answer(self, text=None, show_alert=False):
        self.answers.append((text, show_alert))

    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
        self.edits.append(text)
        self.markups.append(reply_markup)


class FakeMessage:
    def __init__(self) -> None:
        self.replies = []

    async def reply_text(self, text, reply_markup=None, parse_mode=None):
        self.replies.append(text)


class FakeBot:
    def __init__(self) -> None:
        self.messages = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)


class FailingBot:
    async def send_message(self, **kwargs):
        raise errors.TelegramError("delivery failed")


class FakeUpdate:
    def __init__(self, user_id: int, data: str | None = None, message=None) -> None:
        self.effective_user = FakeUser(user_id)
        self.callback_query = FakeQuery(data) if data is not None else None
        self.effective_message = message


class FakeContext:
    def __init__(self) -> None:
        self.user_data = {}
        self.bot = FakeBot()


class FakeApplication:
    def __init__(self) -> None:
        self.handlers = []
        self.error_handlers = []

    def add_handler(self, handler):
        self.handlers.append(handler)

    def add_error_handler(self, handler):
        self.error_handlers.append(handler)


class BookingHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        self.old_admin_id = config.ADMIN_CHAT_ID
        database.DB_PATH = os.path.join(self.tmp.name, "test.db")
        config.ADMIN_CHAT_ID = 999
        database.init_db()

    def tearDown(self) -> None:
        database.DB_PATH = self.old_db_path
        config.ADMIN_CHAT_ID = self.old_admin_id
        self.tmp.cleanup()

    def _hold(self, user_id: int = 1, ttl: int = 300):
        return database.create_hold(
            user_id,
            "client",
            SERVICE,
            SLOT_DATE,
            SLOT_TIME,
            ttl_seconds=ttl,
        )

    def _state(self, hold: dict) -> FakeContext:
        context = FakeContext()
        context.user_data[config.BOOKING_FLOW_KEY] = {
            "service": SERVICE,
            "date": SLOT_DATE,
            "time": SLOT_TIME,
            "hold_id": hold["id"],
            "expires_at": hold["expires_at"],
        }
        return context

    async def test_new_service_selection_releases_old_hold(self) -> None:
        hold = self._hold()
        context = self._state(hold)
        update = FakeUpdate(1, f"{keyboards.CB_SERVICE_PREFIX}styling")

        await user.select_service(update, context)

        self.assertEqual(database.get_booking(hold["id"])["status"], "cancelled")
        self.assertNotIn("t1", database.get_occupied_time_ids("2026-10-27"))

    async def test_expired_confirm_returns_to_time_selection(self) -> None:
        hold = self._hold(ttl=-1)
        context = self._state(hold)
        update = FakeUpdate(1, keyboards.CB_BOOK_CONFIRM)

        await user.confirm_booking(update, context)

        self.assertEqual(update.callback_query.answers[-1][0], texts.ALERT_HOLD_EXPIRED)
        self.assertIn("Оберіть час", update.callback_query.edits[-1])
        self.assertEqual(database.get_booking(hold["id"])["status"], "expired")

    async def test_duplicate_confirm_creates_one_request(self) -> None:
        hold = self._hold()
        context = self._state(hold)
        first = FakeUpdate(1, keyboards.CB_BOOK_CONFIRM)
        second = FakeUpdate(1, keyboards.CB_BOOK_CONFIRM)

        await user.confirm_booking(first, context)
        await user.confirm_booking(second, context)

        pending = database.get_pending_bookings()
        self.assertEqual(len(pending), 1)
        self.assertTrue(first.callback_query.answers[-1][0] is None)
        self.assertEqual(second.callback_query.answers[-1][0], texts.ALERT_HOLD_EXPIRED)

    async def test_foreign_request_is_not_visible(self) -> None:
        hold = self._hold()
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        update = FakeUpdate(2, f"{keyboards.CB_REQUEST_VIEW_PREFIX}{hold['id']}")
        context = FakeContext()

        await user.show_request_view(update, context)

        self.assertEqual(update.callback_query.answers[-1][0], texts.ALERT_REQUEST_NOT_FOUND)
        self.assertEqual(update.callback_query.edits, [])

    async def test_back_from_summary_releases_hold(self) -> None:
        hold = self._hold()
        context = self._state(hold)
        update = FakeUpdate(1, keyboards.CB_BOOK_TIMES)

        await user.show_times(update, context)

        self.assertEqual(database.get_booking(hold["id"])["status"], "cancelled")
        self.assertNotIn("t1", database.get_occupied_time_ids("2026-10-27"))

    async def test_booking_home_releases_hold(self) -> None:
        hold = self._hold()
        context = self._state(hold)
        update = FakeUpdate(1, keyboards.CB_BOOK_HOME)

        await user.booking_home(update, context)

        self.assertEqual(database.get_booking(hold["id"])["status"], "cancelled")
        self.assertNotIn("t1", database.get_occupied_time_ids("2026-10-27"))
        self.assertNotIn(config.BOOKING_FLOW_KEY, context.user_data)

    async def test_menu_command_releases_hold(self) -> None:
        hold = self._hold()
        context = self._state(hold)
        message = FakeMessage()
        update = FakeUpdate(1, message=message)

        await common.menu_command(update, context)

        self.assertEqual(database.get_booking(hold["id"])["status"], "cancelled")
        self.assertNotIn("t1", database.get_occupied_time_ids("2026-10-27"))
        self.assertNotIn(config.BOOKING_FLOW_KEY, context.user_data)

    async def test_repeated_master_confirmation_is_safe(self) -> None:
        hold = self._hold()
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        first = FakeUpdate(
            999,
            f"{keyboards.CB_MASTER_CONFIRM_PREFIX}{hold['id']}",
        )
        second = FakeUpdate(
            999,
            f"{keyboards.CB_MASTER_CONFIRM_PREFIX}{hold['id']}",
        )

        await admin.confirm_request(first, FakeContext())
        await admin.confirm_request(second, FakeContext())

        self.assertEqual(database.get_booking(hold["id"])["status"], "confirmed")
        self.assertEqual(second.callback_query.answers[-1][0], texts.ALERT_BOOKING_PROCESSED)

    async def test_non_admin_cannot_confirm_foreign_request(self) -> None:
        hold = self._hold()
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        update = FakeUpdate(
            2,
            f"{keyboards.CB_MASTER_CONFIRM_PREFIX}{hold['id']}",
        )

        await admin.confirm_request(update, FakeContext())

        self.assertEqual(database.get_booking(hold["id"])["status"], "pending")
        self.assertEqual(update.callback_query.answers[-1][0], texts.NO_ACCESS)

    async def test_new_request_notifies_admin(self) -> None:
        hold = self._hold()
        context = self._state(hold)
        update = FakeUpdate(1, keyboards.CB_BOOK_CONFIRM)

        await user.confirm_booking(update, context)

        self.assertTrue(
            any(message["chat_id"] == 999 for message in context.bot.messages)
        )

    async def test_master_confirmation_notifies_client(self) -> None:
        hold = self._hold()
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        context = FakeContext()
        update = FakeUpdate(999, f"{keyboards.CB_MASTER_CONFIRM_PREFIX}{hold['id']}")

        await admin.confirm_request(update, context)

        self.assertTrue(
            any(message["chat_id"] == 1 for message in context.bot.messages)
        )

    async def test_client_cancel_handler_frees_slot(self) -> None:
        future_date = {"id": "2099-01-05", "label": "5 січня"}
        hold = database.create_hold(
            1,
            "client",
            SERVICE,
            future_date,
            {"id": "10:00", "label": "10:00"},
        )
        self.assertIsNotNone(hold)
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        context = FakeContext()
        update = FakeUpdate(1, f"{keyboards.CB_REQUEST_VIEW_PREFIX}{hold['id']}")
        await user.show_request_view(update, context)

        cancel = FakeUpdate(1, f"{keyboards.CB_CANCEL_REQUEST_PREFIX}{hold['id']}")
        await user.cancel_request(cancel, context)

        self.assertEqual(database.get_booking(hold["id"])["status"], "cancelled")
        self.assertTrue(
            any(message["chat_id"] == 999 for message in context.bot.messages)
        )
        self.assertEqual(cancel.callback_query.answers[-1][0], "Запис скасовано.")

    async def test_delivery_failure_does_not_raise(self) -> None:
        hold = self._hold()
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        booking = database.get_booking(hold["id"])
        self.assertFalse(
            await notifications.notify_admin_new_request(FailingBot(), booking)
        )

    async def test_admin_requests_are_paginated(self) -> None:
        for hour in range(10, 16):
            time_id = f"{hour:02d}:00"
            hold = database.create_hold(
                1,
                "client",
                SERVICE,
                SLOT_DATE,
                {"id": time_id, "label": time_id},
            )
            self.assertIsNotNone(hold)
            self.assertIsNotNone(database.submit_hold(hold["id"], 1))

        update = FakeUpdate(999, keyboards.CB_ADMIN_REQUESTS)
        await admin.show_requests(update, FakeContext())

        self.assertIn("стор. 1/2", update.callback_query.edits[-1])
        self.assertIn("Усього: 6", update.callback_query.edits[-1])

    async def test_full_booking_flow_uses_dynamic_schedule(self) -> None:
        context = FakeContext()
        start = FakeUpdate(1, keyboards.CB_BOOK)
        await user.show_booking(start, context)

        service = config.SERVICES_BY_ID["haircut"]
        service_update = FakeUpdate(
            1,
            f"{keyboards.CB_SERVICE_PREFIX}{service['id']}",
        )
        await user.select_service(service_update, context)

        dates = schedule.available_dates(
            service,
            occupied_lookup=database.get_occupied_intervals,
        )
        self.assertTrue(dates)
        date_id, _label = dates[0]
        date_update = FakeUpdate(1, f"{keyboards.CB_DATE_PREFIX}{date_id}")
        await user.select_date(date_update, context)

        slots = schedule.available_slots(
            date_id,
            service,
            database.get_occupied_intervals(date_id),
        )
        self.assertTrue(slots)
        time_id, _time_label = slots[0]
        time_update = FakeUpdate(1, f"{keyboards.CB_TIME_PREFIX}{time_id}")
        await user.select_time(time_update, context)
        self.assertIsNotNone(context.user_data[config.BOOKING_FLOW_KEY]["hold_id"])

        confirm = FakeUpdate(1, keyboards.CB_BOOK_CONFIRM)
        await user.confirm_booking(confirm, context)

        self.assertEqual(database.get_pending_bookings()[0]["status"], "pending")
        self.assertNotIn(config.BOOKING_FLOW_KEY, context.user_data)

    async def test_admin_filter_callback(self) -> None:
        hold = self._hold()
        self.assertIsNotNone(database.submit_hold(hold["id"], 1))
        self.assertTrue(database.confirm_booking(hold["id"]))

        update = FakeUpdate(999, "admin:requests:confirmed:1")
        await admin.show_requests(update, FakeContext())

        self.assertIn("Підтверджені", update.callback_query.edits[-1])
        markup = update.callback_query.markups[-1]
        labels = [
            button.text
            for row in markup.inline_keyboard
            for button in row
        ]
        self.assertTrue(any("#1" in label for label in labels))

    async def test_registration_covers_all_keyboard_callbacks(self) -> None:
        application = FakeApplication()
        register_handlers(application)

        booking = {
            "id": 1,
            "service_name": "Стрижка",
            "date_label": "27 жовтня",
            "time_label": "10:00",
        }
        keyboards_to_check = [
            keyboards.main_menu_keyboard(False),
            keyboards.main_menu_keyboard(True),
            keyboards.admin_menu_keyboard(),
            keyboards.service_selection_keyboard(),
            keyboards.date_selection_keyboard([("2026-10-27", "27 жовтня")]),
            keyboards.time_selection_keyboard([("10:00", "10:00")]),
            keyboards.booking_summary_keyboard(),
            keyboards.booking_success_keyboard(),
            keyboards.request_list_keyboard([booking]),
            keyboards.request_view_keyboard(1, cancel=True),
            keyboards.request_view_keyboard(1, master=True),
            keyboards.admin_requests_keyboard([booking], "pending", 1, 2),
            keyboards.master_actions_keyboard(1),
            keyboards.back_home_keyboard(keyboards.CB_ADMIN),
        ]
        callbacks = {
            button.callback_data
            for markup in keyboards_to_check
            for row in markup.inline_keyboard
            for button in row
        }
        specific = [
            handler
            for handler in application.handlers
            if isinstance(handler, CallbackQueryHandler) and handler.pattern
        ]
        unmatched = [
            data
            for data in callbacks
            if not any(re.match(handler.pattern, data) for handler in specific)
        ]
        duplicates = {
            handler.pattern
            for handler in specific
            if sum(1 for other in specific if other.pattern == handler.pattern) > 1
        }
        self.assertEqual(unmatched, [])
        self.assertEqual(duplicates, set())
        self.assertTrue(all(len(data.encode()) <= 64 for data in callbacks))
        self.assertIsNone(application.handlers[-1].pattern)


if __name__ == "__main__":
    unittest.main()
