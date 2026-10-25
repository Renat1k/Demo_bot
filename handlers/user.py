import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import CallbackQuery, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config import (
    BOOKING_FLOW_KEY,
    SERVICES_BY_ID,
    TIMEZONE,
    is_admin,
)
from database import (
    cancel_user_booking,
    create_hold,
    get_booking,
    get_occupied_intervals,
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
    CB_CANCEL_REQUEST_PREFIX,
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
from notifications import notify_admin_client_cancelled, notify_admin_new_request
from schedule import (
    available_dates,
    available_slots,
    can_cancel,
    date_label,
    is_within_booking_window,
)
from texts import (
    ALERT_CANCEL_FORBIDDEN,
    ALERT_CANCEL_UNAVAILABLE,
    ALERT_DATE_UNAVAILABLE,
    ALERT_HOLD_EXPIRED,
    ALERT_REQUEST_NOT_FOUND,
    ALERT_SELECT_DATE,
    ALERT_SELECT_SERVICE,
    ALERT_SERVICE_NOT_FOUND,
    ALERT_SLOT_TAKEN,
    ALERT_TIME_NOT_FOUND,
    BOOKING_DATE_EMPTY,
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
    client_label,
    contacts_text,
    request_view_text,
    services_text,
)
from .common import safe_edit_text

BOOKING_KEY = BOOKING_FLOW_KEY


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


async def _render_dates(query: CallbackQuery, service: dict) -> None:
    dates = available_dates(service, occupied_lookup=get_occupied_intervals)
    text = BOOKING_DATE_TITLE
    if not dates:
        text = f"{text}\n\n{BOOKING_DATE_EMPTY}"
    await safe_edit_text(query, text, date_selection_keyboard(dates))


async def _render_times(query: CallbackQuery, date_id: str, service: dict) -> None:
    occupied = get_occupied_intervals(date_id)
    available = available_slots(date_id, service, occupied)
    text = BOOKING_TIME_TITLE
    if not available:
        text = f"{text}\n\n{BOOKING_TIME_EMPTY}"
    await safe_edit_text(query, text, time_selection_keyboard(available))


async def _render_preview(query: CallbackQuery, booking: dict) -> None:
    service = booking["service"]
    text = booking_summary_text(
        service=service["name"],
        date=booking["date"]["label"],
        time=booking["time"]["label"],
        hold_until=_format_hold_until(booking.get("expires_at")),
        price=service.get("price"),
        duration_minutes=service.get("duration_minutes"),
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
    await _render_dates(query, service)


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
    service = booking["service"]
    if not is_within_booking_window(date_id):
        await query.answer(ALERT_DATE_UNAVAILABLE, show_alert=True)
        await _render_dates(query, service)
        return
    times = available_slots(date_id, service, get_occupied_intervals(date_id))
    if not times:
        await query.answer(ALERT_DATE_UNAVAILABLE, show_alert=True)
        await _render_dates(query, service)
        return
    _release_current_hold(update, context)
    await query.answer()
    booking["date"] = {"id": date_id, "label": date_label(date_id)}
    await _render_times(query, date_id, service)


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
        await _render_dates(query, booking["service"])
        return
    time_id = query.data.removeprefix(CB_TIME_PREFIX)
    service = booking["service"]
    available = available_slots(
        booking["date"]["id"],
        service,
        get_occupied_intervals(booking["date"]["id"]),
    )
    if time_id not in {slot_id for slot_id, _label in available}:
        await query.answer(ALERT_TIME_NOT_FOUND, show_alert=True)
        await _render_times(query, booking["date"]["id"], service)
        return

    user_id = _user_id(update)
    if user_id is None:
        await query.answer()
        return
    username = update.effective_user.username if update.effective_user else ""
    hold = create_hold(
        user_id=user_id,
        username=username or "",
        service=service,
        slot_date=booking["date"],
        slot_time={"id": time_id, "label": time_id},
    )
    if hold is None:
        await query.answer(ALERT_SLOT_TAKEN, show_alert=True)
        await _render_times(query, booking["date"]["id"], service)
        return

    await query.answer()
    booking["time"] = {"id": time_id, "label": time_id}
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
    await _render_dates(query, booking["service"])


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
        await _render_dates(query, booking["service"])
        return
    _release_current_hold(update, context)
    await query.answer()
    await _render_times(query, booking["date"]["id"], booking["service"])


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    booking = _booking(context)
    hold_id = booking.get("hold_id")
    user_id = _user_id(update)
    if not hold_id or user_id is None:
        await query.answer(ALERT_HOLD_EXPIRED, show_alert=True)
        service = booking.get("service")
        if service is not None and "date" in booking:
            await _render_times(query, booking["date"]["id"], service)
        elif service is not None:
            await _render_dates(query, service)
        else:
            await _render_services(query)
        return

    submitted = submit_hold(int(hold_id), user_id)
    if submitted is None:
        booking.pop("hold_id", None)
        booking.pop("expires_at", None)
        booking.pop("time", None)
        await query.answer(ALERT_HOLD_EXPIRED, show_alert=True)
        service = booking.get("service")
        if service is not None and "date" in booking:
            await _render_times(query, booking["date"]["id"], service)
        elif service is not None:
            await _render_dates(query, service)
        else:
            await _render_services(query)
        return

    context.user_data.pop(BOOKING_KEY, None)
    await query.answer()
    await notify_admin_new_request(context.bot, submitted)
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


async def _render_request_view(
    query: CallbackQuery,
    booking: dict,
    user_id: int | None,
) -> None:
    admin = is_admin(user_id)
    text = request_view_text(
        request_id=booking["id"],
        service=booking["service_name"],
        date=booking["date_label"],
        time=booking["time_label"],
        status=booking_status_label(booking["status"]),
        price=booking.get("price_label"),
        duration_minutes=booking.get("duration_minutes"),
        client=client_label(booking) if admin else None,
    )
    await safe_edit_text(
        query,
        text,
        request_view_keyboard(
            request_id=booking["id"],
            back_callback=CB_ADMIN_REQUESTS if admin else CB_RECORDS,
            master=admin and booking["status"] == "pending",
            cancel=(
                not admin
                and booking["user_id"] == user_id
                and can_cancel(booking)
            ),
        ),
    )


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

    await query.answer()
    await _render_request_view(query, booking, user_id)


async def cancel_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    try:
        request_id = int(query.data.removeprefix(CB_CANCEL_REQUEST_PREFIX))
    except ValueError:
        await query.answer(ALERT_REQUEST_NOT_FOUND, show_alert=True)
        return

    booking = get_booking(request_id)
    user_id = _user_id(update)
    if booking is None or booking["user_id"] != user_id:
        await query.answer(ALERT_CANCEL_FORBIDDEN, show_alert=True)
        return
    updated = cancel_user_booking(request_id, user_id)
    if updated is None:
        await query.answer(ALERT_CANCEL_UNAVAILABLE, show_alert=True)
        return

    await query.answer("Запис скасовано.")
    await notify_admin_client_cancelled(context.bot, updated)
    await _render_request_view(query, updated, user_id)


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
            pattern=rf"^{re.escape(CB_TIME_PREFIX)}[0-9:]+$",
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
    application.add_handler(
        CallbackQueryHandler(
            cancel_request,
            pattern=rf"^{re.escape(CB_CANCEL_REQUEST_PREFIX)}[0-9]+$",
        )
    )
