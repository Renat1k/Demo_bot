import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from config import DEMO_REQUEST_ID, is_admin
from keyboards import (
    CB_ADMIN,
    CB_ADMIN_REQUESTS,
    CB_ADMIN_SCHEDULE,
    CB_ADMIN_SETTINGS,
    CB_MASTER_ACTIONS_PREFIX,
    CB_MASTER_CONFIRM_PREFIX,
    CB_MASTER_REJECT_PREFIX,
    CB_MASTER_RESCHEDULE_PREFIX,
    admin_menu_keyboard,
    back_home_keyboard,
    master_actions_keyboard,
    request_list_keyboard,
)
from texts import (
    ADMIN_PANEL,
    ADMIN_REQUESTS,
    ADMIN_SCHEDULE,
    ADMIN_SETTINGS,
    ALERT_REQUEST_NOT_FOUND,
    MASTER_ACTIONS_TITLE,
    MASTER_CONFIRM_STUB,
    MASTER_REJECT_STUB,
    MASTER_RESCHEDULE_STUB,
    NO_ACCESS,
)
from .common import safe_edit_text


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
    await safe_edit_text(
        query,
        ADMIN_REQUESTS,
        request_list_keyboard(back_callback=CB_ADMIN),
    )


async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    await query.answer()
    await safe_edit_text(query, ADMIN_SCHEDULE, back_home_keyboard(CB_ADMIN))


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    await query.answer()
    await safe_edit_text(query, ADMIN_SETTINGS, back_home_keyboard(CB_ADMIN))


async def show_master_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    request_id = query.data.removeprefix(CB_MASTER_ACTIONS_PREFIX)
    if request_id != DEMO_REQUEST_ID:
        await query.answer(ALERT_REQUEST_NOT_FOUND, show_alert=True)
        return
    await query.answer()
    await safe_edit_text(query, MASTER_ACTIONS_TITLE, master_actions_keyboard(request_id))


async def _show_master_result(
    update: Update,
    text: str,
    callback_prefix: str,
) -> None:
    if not await _check_admin_callback(update):
        return
    query = update.callback_query
    request_id = query.data.removeprefix(callback_prefix)
    if request_id != DEMO_REQUEST_ID:
        await query.answer(ALERT_REQUEST_NOT_FOUND, show_alert=True)
        return
    await query.answer()
    await safe_edit_text(
        query,
        text,
        back_home_keyboard(f"{CB_MASTER_ACTIONS_PREFIX}{request_id}"),
    )


async def confirm_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_master_result(update, MASTER_CONFIRM_STUB, CB_MASTER_CONFIRM_PREFIX)


async def reject_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_master_result(update, MASTER_REJECT_STUB, CB_MASTER_REJECT_PREFIX)


async def reschedule_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_master_result(
        update,
        MASTER_RESCHEDULE_STUB,
        CB_MASTER_RESCHEDULE_PREFIX,
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
        CallbackQueryHandler(show_schedule, pattern=rf"^{re.escape(CB_ADMIN_SCHEDULE)}$")
    )
    application.add_handler(
        CallbackQueryHandler(show_settings, pattern=rf"^{re.escape(CB_ADMIN_SETTINGS)}$")
    )
    application.add_handler(
        CallbackQueryHandler(
            show_master_actions,
            pattern=rf"^{re.escape(CB_MASTER_ACTIONS_PREFIX)}[A-Za-z0-9_-]+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            confirm_request,
            pattern=rf"^{re.escape(CB_MASTER_CONFIRM_PREFIX)}[A-Za-z0-9_-]+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            reject_request,
            pattern=rf"^{re.escape(CB_MASTER_REJECT_PREFIX)}[A-Za-z0-9_-]+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            reschedule_request,
            pattern=rf"^{re.escape(CB_MASTER_RESCHEDULE_PREFIX)}[A-Za-z0-9_-]+$",
        )
    )
