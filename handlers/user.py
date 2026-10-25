import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import CallbackQuery, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config import (
    BOOKING_FLOW_KEY,
    DEMO_DATES,
    DEMO_TIMES,
    SERVICES,
    TIMEZONE,
    is_admin,
)
from database import (
    create_hold,
    get_booking,
    get_occupied_time_ids,
    get_user_bookings,
    release_hold,
    release_user_holds,
    submit_hold,
)
from keyboards import (
    CB_ADMIN_REQUESTS,
    CB_BOOK,
    CB_BOOK_CANCEL,
    CB_BOOK_CONFIRM,
    CB_BOOK_DATES,
    CB_BOOK_HOME,
    CB_BOOK_TIMES,
    CB_CONTACTS,
    CB_DATE_PREFIX,
    CB_RECORDS,
    CB_REQUEST_VIEW_PREFIX,
    CB_SERVICE_PREFIX,
    CB_SERVICES,
    CB_TIME_PREFIX,
    booking_success_keyboard,
    booking_summary_keyboard,
    date_selection_keyboard,
    home_keyboard,
    main_menu_keyboard,
    request_list_keyboard,
    request_view_keyboard,
    service_selection_keyboard,
    time_selection_keyboard,
)
from texts import (
    ALERT_DATE_NOT_FOUND,
    ALERT_HOLD_EXPIRED,
    ALERT_REQUEST_NOT_FOUND,
    ALERT_SELECT_DATE,
    ALERT_SELECT_SERVICE,
    ALERT_SERVICE_NOT_FOUND,
    ALERT_SLOT_TAKEN,
    ALERT_TIME_NOT_FOUND,
    BOOKING_DATE_TITLE,
    BOOKING_SERVICE_TITLE,
    BOOKING_TIME_EMPTY,
    BOOKING_TIME_TITLE,
    MAIN_MENU,
    RECORDS_EMPTY,
    RECORDS_TITLE,
    booking_status_label,
    booking_submitted_text,
    booking_summary_text,
    contacts_text,
    request_view_text,
    services_text,
)
from .common import safe_edit_text

BOOKING_KEY = BOOKING_FLOW_KEY
SERVICES_BY_ID = {
    service_id: {"id": service_id, "name": name, "price": price}
    for service_id, name, price in SERVICES
}
DATES_BY_ID = dict(DEMO_DATES)
TIMES_BY_ID = dict(DEMO_TIMES)


def _user_id(update: Update) -> int | None:
    return update.effective_user.id if update.effective_user else None


def _booking(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.get(BOOKING_KEY, {})


def _format_hold_until(value: str | None) -> str:
    if not value:
        return "—"
    try:
        local = (
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            .replace(tzinfo=timezone.utc)
            .astimezone(ZoneInfo(TIMEZONE))
        )
        return local.strftime("%H:%M")
    except (ValueError, ZoneInfoNotFoundError):
        return f"{value[11:16]} UTC"


async def _render_services(query: CallbackQuery) -> None:
    await safe_edit_text(query, BOOKING_SERVICE_TITLE, service_selection_keyboard())


async def _render_dates(query: CallbackQuery) -> None:
    await safe_edit_text(query, BOOKING_DATE_TITLE, date_selection_keyboard())


async def _render_times(query: CallbackQuery, date_id: str) -> None:
    occupied = get_occupied_time_ids(date_id)
    available = {time_id for time_id, _label in DEMO_TIMES} - occupied
    text = BOOKING_TIME_TITLE
    if not available:
        text = f"{text}\n\n{BOOKING_TIME_EMPTY}"
    await safe_edit_text(query, text, time_selection_keyboard(available))


async def _render_preview(query: CallbackQuery, booking: dict) -> None:
    text = booking_summary_text(
        service=booking["service"]["name"],
        date=booking["date"]["label"],
        time=booking["time"]["label"],
        hold_until=_format_hold_until(booking.get("expires_at")),
    )
    await safe_edit_text(query, text, booking_summary_keyboard())


def _release_current_hold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    booking = _booking(context)
    hold_id = booking.get("hold_id")
    user_id = _user_id(update)
    if hold_id and user_id is not None:
        release_hold(int(hold_id), user_id)
    booking.pop("hold_id", None)
    booking.pop("expires_at", None)
    booking.pop("time", None)


async def show_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    user_id = _user_id(update)
    if user_id is not None:
        release_user_holds(user_id)
    context.user_data.pop(BOOKING_KEY, None)
    await query.answer()
    await _render_services(query)


async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    service_id = query.data.removeprefix(CB_SERVICE_PREFIX)
    service = SERVICES_BY_ID.get(service_id)
    if service is None:
        await query.answer(ALERT_SERVICE_NOT_FOUND, show_alert=True)
        await _render_services(query)
        return
    user_id = _user_id(update)
    if user_id is not None:
        release_user_holds(user_id)
    await query.answer()
    context.user_data[BOOKING_KEY] = {"service": service}
    await _render_dates(query)


async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    booking = _booking(context)
    if "service" not in booking:
        await query.answer(ALERT_SELECT_SERVICE, show_alert=True)
        await _render_services(query)
        return
    date_id = query.data.removeprefix(CB_DATE_PREFIX)
    date_label = DATES_BY_ID.get(date_id)
    if date_label is None:
        await query.answer(ALERT_DATE_NOT_FOUND, show_alert=True)
        await _render_dates(query)
        return
    _release_current_hold(update, context)
    await query.answer()
    booking["date"] = {"id": date_id, "label": date_label}
    await _render_times(query, date_id)


async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    booking = _booking(context)
    if "service" not in booking:
        await query.answer(ALERT_SELECT_SERVICE, show_alert=True)
        await _render_services(query)
        return
    if "date" not in booking:
        await query.answer(ALERT_SELECT_DATE, show_alert=True)
        await _render_dates(query)
        return
    time_id = query.data.removeprefix(CB_TIME_PREFIX)
    time_label = TIMES_BY_ID.get(time_id)
    if time_label is None:
        await query.answer(ALERT_TIME_NOT_FOUND, show_alert=True)
        await _render_times(query, booking["date"]["id"])
        return

    user_id = _user_id(update)
    if user_id is None:
        await query.answer()
        return
    username = update.effective_user.username if update.effective_user else ""
    hold = create_hold(
        user_id=user_id,
        username=username or "",
        service=booking["service"],
        slot_date=booking["date"],
        slot_time={"id": time_id, "label": time_label},
    )
    if hold is None:
        await query.answer(ALERT_SLOT_TAKEN, show_alert=True)
        await _render_times(query, booking["date"]["id"])
        return

    await query.answer()
    booking["time"] = {"id": time_id, "label": time_label}
    booking["hold_id"] = hold["id"]
    booking["expires_at"] = hold["expires_at"]
    await _render_preview(query, booking)


async def show_dates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    booking = _booking(context)
    if "service" not in booking:
        await query.answer(ALERT_SELECT_SERVICE, show_alert=True)
        await _render_services(query)
        return
    _release_current_hold(update, context)
    await query.answer()
    await _render_dates(query)


async def show_times(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    booking = _booking(context)
    if "service" not in booking:
        await query.answer(ALERT_SELECT_SERVICE, show_alert=True)
        await _render_services(query)
        return
    if "date" not in booking:
        await query.answer(ALERT_SELECT_DATE, show_alert=True)
        await _render_dates(query)
        return
    _release_current_hold(update, context)
    await query.answer()
    await _render_times(query, booking["date"]["id"])


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    booking = _booking(context)
    hold_id = booking.get("hold_id")
    user_id = _user_id(update)
    if not hold_id or user_id is None:
        await query.answer(ALERT_HOLD_EXPIRED, show_alert=True)
        if "date" in booking:
            await _render_times(query, booking["date"]["id"])
        else:
            await _render_services(query)
        return

    submitted = submit_hold(int(hold_id), user_id)
    if submitted is None:
        booking.pop("hold_id", None)
        booking.pop("expires_at", None)
        booking.pop("time", None)
        await query.answer(ALERT_HOLD_EXPIRED, show_alert=True)
        if "date" in booking:
            await _render_times(query, booking["date"]["id"])
        else:
            await _render_services(query)
        return

    context.user_data.pop(BOOKING_KEY, None)
    await query.answer()
    await safe_edit_text(
        query,
        booking_submitted_text(
            booking_id=submitted["id"],
            status=booking_status_label(submitted["status"]),
        ),
        booking_success_keyboard(),
    )


async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    user_id = _user_id(update)
    if user_id is not None:
        release_user_holds(user_id)
    context.user_data.pop(BOOKING_KEY, None)
    await query.answer()
    await _render_services(query)


async def booking_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    user_id = _user_id(update)
    if user_id is not None:
        release_user_holds(user_id)
    context.user_data.pop(BOOKING_KEY, None)
    await query.answer()
    await safe_edit_text(
        query,
        MAIN_MENU,
        main_menu_keyboard(is_admin(user_id)),
    )


async def show_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    await safe_edit_text(query, services_text(), home_keyboard())


async def show_records(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    user_id = _user_id(update)
    bookings = get_user_bookings(user_id) if user_id is not None else []
    await query.answer()
    if not bookings:
        await safe_edit_text(query, RECORDS_EMPTY, home_keyboard())
        return
    await safe_edit_text(
        query,
        RECORDS_TITLE,
        request_list_keyboard(bookings),
    )


async def show_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    await safe_edit_text(query, contacts_text(), home_keyboard())


async def show_request_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    try:
        request_id = int(query.data.removeprefix(CB_REQUEST_VIEW_PREFIX))
    except ValueError:
        await query.answer(ALERT_REQUEST_NOT_FOUND, show_alert=True)
        return

    booking = get_booking(request_id)
    user_id = _user_id(update)
    admin = is_admin(user_id)
    if booking is None or (not admin and booking["user_id"] != user_id):
        await query.answer(ALERT_REQUEST_NOT_FOUND, show_alert=True)
        return

    text = request_view_text(
        request_id=booking["id"],
        service=booking["service_name"],
        date=booking["date_label"],
        time=booking["time_label"],
        status=booking_status_label(booking["status"]),
    )
    await query.answer()
    await safe_edit_text(
        query,
        text,
        request_view_keyboard(
            request_id=booking["id"],
            back_callback=CB_ADMIN_REQUESTS if admin else CB_RECORDS,
            master=admin and booking["status"] == "pending",
        ),
    )


def register(application: Application) -> None:
    application.add_handler(
        CallbackQueryHandler(show_booking, pattern=rf"^{re.escape(CB_BOOK)}$")
    )
    application.add_handler(
        CallbackQueryHandler(show_services, pattern=rf"^{re.escape(CB_SERVICES)}$")
    )
    application.add_handler(
        CallbackQueryHandler(show_records, pattern=rf"^{re.escape(CB_RECORDS)}$")
    )
    application.add_handler(
        CallbackQueryHandler(show_contacts, pattern=rf"^{re.escape(CB_CONTACTS)}$")
    )
    application.add_handler(
        CallbackQueryHandler(
            select_service,
            pattern=rf"^{re.escape(CB_SERVICE_PREFIX)}[a-z0-9_]+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(show_dates, pattern=rf"^{re.escape(CB_BOOK_DATES)}$")
    )
    application.add_handler(
        CallbackQueryHandler(
            select_date,
            pattern=rf"^{re.escape(CB_DATE_PREFIX)}\d{{4}}-\d{{2}}-\d{{2}}$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(show_times, pattern=rf"^{re.escape(CB_BOOK_TIMES)}$")
    )
    application.add_handler(
        CallbackQueryHandler(
            select_time,
            pattern=rf"^{re.escape(CB_TIME_PREFIX)}[a-z0-9]+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(confirm_booking, pattern=rf"^{re.escape(CB_BOOK_CONFIRM)}$")
    )
    application.add_handler(
        CallbackQueryHandler(cancel_booking, pattern=rf"^{re.escape(CB_BOOK_CANCEL)}$")
    )
    application.add_handler(
        CallbackQueryHandler(booking_home, pattern=rf"^{re.escape(CB_BOOK_HOME)}$")
    )
    application.add_handler(
        CallbackQueryHandler(
            show_request_view,
            pattern=rf"^{re.escape(CB_REQUEST_VIEW_PREFIX)}[0-9]+$",
        )
    )
