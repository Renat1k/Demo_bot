from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from config import is_admin
from .common import safe_edit_text
from keyboards import (
    CB_ADMIN,
    CB_ADMIN_REQUESTS,
    CB_ADMIN_SCHEDULE,
    CB_ADMIN_SETTINGS,
    admin_menu_keyboard,
    admin_section_keyboard,
)
from texts import (
    ADMIN_PANEL,
    ADMIN_REQUESTS,
    ADMIN_SCHEDULE,
    ADMIN_SETTINGS,
    NO_ACCESS,
)


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


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    await query.answer()
    await safe_edit_text(query, ADMIN_PANEL, admin_menu_keyboard())


async def show_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    await query.answer()
    await safe_edit_text(query, ADMIN_REQUESTS, admin_section_keyboard())


async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    await query.answer()
    await safe_edit_text(query, ADMIN_SCHEDULE, admin_section_keyboard())


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    await query.answer()
    await safe_edit_text(query, ADMIN_SETTINGS, admin_section_keyboard())


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
    application.add_handler(CallbackQueryHandler(show_admin_panel, pattern=f"^{CB_ADMIN}$"))
    application.add_handler(
        CallbackQueryHandler(show_requests, pattern=f"^{CB_ADMIN_REQUESTS}$")
    )
    application.add_handler(
        CallbackQueryHandler(show_schedule, pattern=f"^{CB_ADMIN_SCHEDULE}$")
    )
    application.add_handler(
        CallbackQueryHandler(show_settings, pattern=f"^{CB_ADMIN_SETTINGS}$")
    )
