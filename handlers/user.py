import re

from telegram import CallbackQuery, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config import DEMO_DATES, DEMO_REQUEST_ID, DEMO_TIMES, SERVICES, is_admin
from keyboards import (
    CB_ADMIN_REQUESTS,
    CB_BOOK,
    CB_BOOK_CONFIRM,
    CB_BOOK_DATES,
    CB_BOOK_PREVIEW,
    CB_BOOK_TIMES,
    CB_CONTACTS,
    CB_DATE_PREFIX,
    CB_RECORDS,
    CB_REQUEST_VIEW_PREFIX,
    CB_SERVICE_PREFIX,
    CB_SERVICES,
    CB_TIME_PREFIX,
    back_home_keyboard,
    booking_summary_keyboard,
    date_selection_keyboard,
    home_keyboard,
    request_list_keyboard,
    request_view_keyboard,
    service_selection_keyboard,
    time_selection_keyboard,
)
from texts import (
    ALERT_DATE_NOT_FOUND,
    ALERT_REQUEST_NOT_FOUND,
    ALERT_SELECT_DATE,
    ALERT_SELECT_SERVICE,
    ALERT_SERVICE_NOT_FOUND,
    ALERT_TIME_NOT_FOUND,
    BOOKING_CONFIRM_STUB,
    BOOKING_DATE_TITLE,
    BOOKING_SERVICE_TITLE,
    BOOKING_TIME_TITLE,
    RECORDS_STUB,
    STATUS_NEW,
    booking_summary_text,
    contacts_text,
    request_view_text,
    services_text,
)
from .common import safe_edit_text

BOOKING_KEY = "demo_booking"
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


async def _render_services(query: CallbackQuery) -> None:
    await safe_edit_text(query, BOOKING_SERVICE_TITLE, service_selection_keyboard())


async def _render_dates(query: CallbackQuery) -> None:
    await safe_edit_text(query, BOOKING_DATE_TITLE, date_selection_keyboard())


async def _render_times(query: CallbackQuery) -> None:
    await safe_edit_text(query, BOOKING_TIME_TITLE, time_selection_keyboard())


async def _render_preview(query: CallbackQuery, booking: dict) -> None:
    text = booking_summary_text(
        service=booking["service"]["name"],
        date=booking["date"]["label"],
        time=booking["time"]["label"],
    )
    await safe_edit_text(query, text, booking_summary_keyboard())


async def show_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
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
    await query.answer()
    booking["date"] = {"id": date_id, "label": date_label}
    booking.pop("time", None)
    await _render_times(query)


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
        await _render_times(query)
        return
    await query.answer()
    booking["time"] = {"id": time_id, "label": time_label}
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
    await query.answer()
    await _render_times(query)


async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    if "time" not in booking:
        await query.answer(ALERT_TIME_NOT_FOUND, show_alert=True)
        await _render_times(query)
        return
    await query.answer()
    await _render_preview(query, booking)


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    if "time" not in booking:
        await query.answer(ALERT_TIME_NOT_FOUND, show_alert=True)
        await _render_times(query)
        return
    await query.answer()
    await safe_edit_text(
        query,
        BOOKING_CONFIRM_STUB,
        back_home_keyboard(CB_BOOK_PREVIEW),
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
    await query.answer()
    await safe_edit_text(query, RECORDS_STUB, request_list_keyboard())


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
    request_id = query.data.removeprefix(CB_REQUEST_VIEW_PREFIX)
    if request_id != DEMO_REQUEST_ID:
        await query.answer(ALERT_REQUEST_NOT_FOUND, show_alert=True)
        return
    admin = is_admin(_user_id(update))
    service = SERVICES[0]
    date = DEMO_DATES[0]
    time = DEMO_TIMES[1]
    text = request_view_text(
        request_id=DEMO_REQUEST_ID,
        service=service[1],
        date=date[1],
        time=time[1],
        status=STATUS_NEW,
    )
    await query.answer()
    await safe_edit_text(
        query,
        text,
        request_view_keyboard(
            request_id=DEMO_REQUEST_ID,
            back_callback=CB_ADMIN_REQUESTS if admin else CB_RECORDS,
            master=admin,
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
        CallbackQueryHandler(show_preview, pattern=rf"^{re.escape(CB_BOOK_PREVIEW)}$")
    )
    application.add_handler(
        CallbackQueryHandler(confirm_booking, pattern=rf"^{re.escape(CB_BOOK_CONFIRM)}$")
    )
    application.add_handler(
        CallbackQueryHandler(
            show_request_view,
            pattern=rf"^{re.escape(CB_REQUEST_VIEW_PREFIX)}[A-Za-z0-9_-]+$",
        )
    )
