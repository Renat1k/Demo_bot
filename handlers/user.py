from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from keyboards import (
    CB_BOOK,
    CB_CONTACTS,
    CB_RECORDS,
    CB_SERVICES,
    home_keyboard,
)
from texts import BOOKING_STUB, RECORDS_STUB, contacts_text, services_text
from .common import safe_edit_text


async def show_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    await safe_edit_text(query, BOOKING_STUB, home_keyboard())


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
    await safe_edit_text(query, RECORDS_STUB, home_keyboard())


async def show_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    await safe_edit_text(query, contacts_text(), home_keyboard())


def register(application: Application) -> None:
    application.add_handler(CallbackQueryHandler(show_booking, pattern=f"^{CB_BOOK}$"))
    application.add_handler(CallbackQueryHandler(show_services, pattern=f"^{CB_SERVICES}$"))
    application.add_handler(CallbackQueryHandler(show_records, pattern=f"^{CB_RECORDS}$"))
    application.add_handler(CallbackQueryHandler(show_contacts, pattern=f"^{CB_CONTACTS}$"))
