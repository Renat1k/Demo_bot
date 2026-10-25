import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from config import is_admin
from database import (
    confirm_booking,
    count_bookings,
    get_booking,
    get_bookings,
    reject_booking,
)
from notifications import notify_client_status
from keyboards import (
    CB_ADMIN,
    CB_ADMIN_REQUESTS,
    CB_ADMIN_REQUESTS_QUERY_PREFIX,
    CB_ADMIN_SCHEDULE,
    CB_ADMIN_SETTINGS,
    CB_MASTER_ACTIONS_PREFIX,
    CB_MASTER_CONFIRM_PREFIX,
    CB_MASTER_REJECT_PREFIX,
    CB_MASTER_RESCHEDULE_PREFIX,
    CB_REQUEST_VIEW_PREFIX,
    admin_menu_keyboard,
    admin_requests_keyboard,
    back_home_keyboard,
    master_actions_keyboard,
)
from texts import (
    ADMIN_PANEL,
    ALERT_BOOKING_PROCESSED,
    ALERT_REQUEST_NOT_FOUND,
    MASTER_ACTIONS_TITLE,
    MASTER_CONFIRMED,
    MASTER_REJECTED,
    MASTER_RESCHEDULE_STUB,
    NO_ACCESS,
    admin_requests_empty,
    admin_requests_title,
    admin_schedule_text,
    admin_settings_text,
)
from .common import safe_edit_text

REQUESTS_PAGE_SIZE = 5
REQUESTS_FILTERS = ("pending", "confirmed", "all")


def _user_id(update: Update) -> int | None:
    return update.effective_user.id if update.effective_user else None


async def _check_admin_callback(update: Update) -> bool:
    query = update.callback_query
    if query is None:
        return False
    if not is_admin(_user_id(update)):
        await query.answer(NO_ACCESS, show_alert=True)
        return False
    return True


def _request_id(query_data: str, prefix: str) -> int | None:
    try:
        return int(query_data.removeprefix(prefix))
    except ValueError:
        return None


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    await query.answer()
    await safe_edit_text(query, ADMIN_PANEL, admin_menu_keyboard())


def _parse_requests_query(data: str) -> tuple[str, int]:
    if data == CB_ADMIN_REQUESTS:
        return "pending", 1
    suffix = data.removeprefix(CB_ADMIN_REQUESTS_QUERY_PREFIX)
    parts = suffix.split(":")
    if len(parts) != 2:
        return "pending", 1
    filter_key = parts[0] if parts[0] in REQUESTS_FILTERS else "pending"
    try:
        page = int(parts[1])
    except ValueError:
        page = 1
    return filter_key, max(1, page)


async def show_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    filter_key, page = _parse_requests_query(query.data)
    status = None if filter_key == "all" else filter_key
    total = count_bookings(status)
    pages = max(1, (total + REQUESTS_PAGE_SIZE - 1) // REQUESTS_PAGE_SIZE)
    page = min(page, pages)
    bookings = get_bookings(
        status,
        limit=REQUESTS_PAGE_SIZE,
        offset=(page - 1) * REQUESTS_PAGE_SIZE,
    )
    await query.answer()
    if not bookings:
        await safe_edit_text(
            query,
            admin_requests_empty(filter_key),
            admin_requests_keyboard([], filter_key, page, pages),
        )
        return
    await safe_edit_text(
        query,
        admin_requests_title(filter_key, total, page, pages),
        admin_requests_keyboard(bookings, filter_key, page, pages),
    )


async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    await query.answer()
    await safe_edit_text(query, admin_schedule_text(), back_home_keyboard(CB_ADMIN))


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    await query.answer()
    await safe_edit_text(query, admin_settings_text(), back_home_keyboard(CB_ADMIN))


async def show_master_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    request_id = _request_id(query.data, CB_MASTER_ACTIONS_PREFIX)
    booking = get_booking(request_id) if request_id is not None else None
    if booking is None:
        await query.answer(ALERT_REQUEST_NOT_FOUND, show_alert=True)
        return
    if booking["status"] != "pending":
        await query.answer(ALERT_BOOKING_PROCESSED, show_alert=True)
        return
    await query.answer()
    await safe_edit_text(query, MASTER_ACTIONS_TITLE, master_actions_keyboard(request_id))


async def _show_master_result(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    callback_prefix: str,
    action: str,
) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    request_id = _request_id(query.data, callback_prefix)
    booking = get_booking(request_id) if request_id is not None else None
    if booking is None:
        await query.answer(ALERT_REQUEST_NOT_FOUND, show_alert=True)
        return
    if booking["status"] != "pending":
        await query.answer(ALERT_BOOKING_PROCESSED, show_alert=True)
        return
    if action == "confirm":
        updated = confirm_booking(request_id)
    else:
        updated = reject_booking(request_id)
    if not updated:
        await query.answer(ALERT_BOOKING_PROCESSED, show_alert=True)
        return
    await query.answer()
    updated_booking = get_booking(request_id)
    if updated_booking is not None:
        await notify_client_status(context.bot, updated_booking, updated_booking["status"])
    await safe_edit_text(
        query,
        text,
        back_home_keyboard(f"{CB_REQUEST_VIEW_PREFIX}{request_id}"),
    )


async def confirm_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_master_result(
        update,
        context,
        MASTER_CONFIRMED,
        CB_MASTER_CONFIRM_PREFIX,
        "confirm",
    )


async def reject_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_master_result(
        update,
        context,
        MASTER_REJECTED,
        CB_MASTER_REJECT_PREFIX,
        "reject",
    )


async def reschedule_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    request_id = _request_id(query.data, CB_MASTER_RESCHEDULE_PREFIX)
    booking = get_booking(request_id) if request_id is not None else None
    if booking is None:
        await query.answer(ALERT_REQUEST_NOT_FOUND, show_alert=True)
        return
    if booking["status"] != "pending":
        await query.answer(ALERT_BOOKING_PROCESSED, show_alert=True)
        return
    await query.answer()
    await safe_edit_text(
        query,
        MASTER_RESCHEDULE_STUB,
        back_home_keyboard(f"{CB_MASTER_ACTIONS_PREFIX}{request_id}"),
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    if not is_admin(_user_id(update)):
        await message.reply_text(NO_ACCESS)
        return
    await message.reply_text(
        ADMIN_PANEL,
        reply_markup=admin_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )


def register(application: Application) -> None:
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(
        CallbackQueryHandler(show_admin_panel, pattern=rf"^{re.escape(CB_ADMIN)}$")
    )
    application.add_handler(
        CallbackQueryHandler(show_requests, pattern=rf"^{re.escape(CB_ADMIN_REQUESTS)}$")
    )
    application.add_handler(
        CallbackQueryHandler(
            show_requests,
            pattern=(
                rf"^{re.escape(CB_ADMIN_REQUESTS_QUERY_PREFIX)}"
                r"(pending|confirmed|all):[0-9]+$"
            ),
        )
    )
    application.add_handler(
        CallbackQueryHandler(show_schedule, pattern=rf"^{re.escape(CB_ADMIN_SCHEDULE)}$")
    )
    application.add_handler(
        CallbackQueryHandler(show_settings, pattern=rf"^{re.escape(CB_ADMIN_SETTINGS)}$")
    )
    application.add_handler(
        CallbackQueryHandler(
            show_master_actions,
            pattern=rf"^{re.escape(CB_MASTER_ACTIONS_PREFIX)}[0-9]+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            confirm_request,
            pattern=rf"^{re.escape(CB_MASTER_CONFIRM_PREFIX)}[0-9]+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            reject_request,
            pattern=rf"^{re.escape(CB_MASTER_REJECT_PREFIX)}[0-9]+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            reschedule_request,
            pattern=rf"^{re.escape(CB_MASTER_RESCHEDULE_PREFIX)}[0-9]+$",
        )
    )
