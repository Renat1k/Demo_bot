import os
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
import texts
from handlers import admin, common, user


SERVICE = {"id": "haircut", "name": "Стрижка"}
SERVICE_2 = {"id": "styling", "name": "Укладка"}
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

    async def answer(self, text=None, show_alert=False):
        self.answers.append((text, show_alert))

    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
        self.edits.append(text)


class FakeMessage:
    def __init__(self) -> None:
        self.replies = []

    async def reply_text(self, text, reply_markup=None, parse_mode=None):
        self.replies.append(text)


class FakeUpdate:
    def __init__(self, user_id: int, data: str | None = None, message=None) -> None:
        self.effective_user = FakeUser(user_id)
        self.callback_query = FakeQuery(data) if data is not None else None
        self.effective_message = message


class FakeContext:
    def __init__(self) -> None:
        self.user_data = {}


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


if __name__ == "__main__":
    unittest.main()
