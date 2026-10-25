import logging

from telegram import CallbackQuery, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from config import is_admin
from keyboards import CB_MAIN, main_menu_keyboard
from texts import ERROR, HELP, MAIN_MENU, START, UNKNOWN_CALLBACK

logger = logging.getLogger(__name__)


async def safe_edit_text(query: CallbackQuery, text: str, reply_markup=None) -> None:
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    except BadRequest:
        logger.debug("Повідомлення не вдалося змінити (можливо, воно вже актуальне).")


def _user_id(update: Update) -> int | None:
    return update.effective_user.id if update.effective_user else None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(
        START,
        reply_markup=main_menu_keyboard(is_admin(_user_id(update))),
        parse_mode=ParseMode.HTML,
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(
        MAIN_MENU,
        reply_markup=main_menu_keyboard(is_admin(_user_id(update))),
        parse_mode=ParseMode.HTML,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(
        HELP,
        reply_markup=main_menu_keyboard(is_admin(_user_id(update))),
        parse_mode=ParseMode.HTML,
    )


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    await safe_edit_text(
        query,
        MAIN_MENU,
        main_menu_keyboard(is_admin(_user_id(update))),
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Помилка під час обробки оновлення", exc_info=context.error)
    if not isinstance(update, Update):
        return
    if update.callback_query is not None:
        try:
            await update.callback_query.answer()
        except TelegramError:
            pass
    message = update.effective_message
    if message is None:
        return
    try:
        await message.reply_text(ERROR)
    except TelegramError:
        logger.exception("Не вдалося надіслати повідомлення про помилку.")


async def unknown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer(UNKNOWN_CALLBACK, show_alert=True)


def register(application: Application) -> None:
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern=f"^{CB_MAIN}$"))
    application.add_error_handler(error_handler)
