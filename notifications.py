import logging

from telegram.constants import ParseMode
from telegram.error import TelegramError

import config
from keyboards import (
    CB_ADMIN_REQUESTS,
    booking_success_keyboard,
    request_view_keyboard,
)
from texts import (
    admin_client_cancelled_text,
    admin_new_request_text,
    client_status_text,
)

logger = logging.getLogger(__name__)


async def _safe_send(bot, chat_id: int | None, text: str, reply_markup=None) -> bool:
    if bot is None or chat_id is None:
        return False
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
        return True
    except TelegramError:
        logger.warning(
            "Не вдалося доставити повідомлення chat_id=%s",
            chat_id,
            exc_info=True,
        )
        return False


async def notify_admin_new_request(bot, booking: dict) -> bool:
    if config.ADMIN_CHAT_ID is None:
        logger.info("ADMIN_CHAT_ID не задано: сповіщення майстру пропущено.")
        return False
    return await _safe_send(
        bot,
        config.ADMIN_CHAT_ID,
        admin_new_request_text(booking),
        request_view_keyboard(
            booking["id"],
            back_callback=CB_ADMIN_REQUESTS,
            master=True,
        ),
    )


async def notify_client_status(bot, booking: dict, status: str) -> bool:
    return await _safe_send(
        bot,
        booking.get("user_id"),
        client_status_text(booking, status),
        booking_success_keyboard(),
    )


async def notify_admin_client_cancelled(bot, booking: dict) -> bool:
    if config.ADMIN_CHAT_ID is None:
        return False
    return await _safe_send(
        bot,
        config.ADMIN_CHAT_ID,
        admin_client_cancelled_text(booking),
        request_view_keyboard(
            booking["id"],
            back_callback=CB_ADMIN_REQUESTS,
            master=False,
        ),
    )
