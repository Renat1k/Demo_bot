import json
import logging
import urllib.error
import urllib.request

import config
import texts

logger = logging.getLogger(__name__)


def _webapp_markup() -> dict | None:
    if not config.WEBAPP_URL.startswith("https://"):
        return None
    return {
        "inline_keyboard": [
            [
                {
                    "text": texts.BTN_WEBAPP,
                    "web_app": {"url": config.WEBAPP_URL},
                }
            ]
        ]
    }


def send_message(chat_id: int | None, text: str, reply_markup: dict | None = None) -> bool:
    if chat_id is None or not config.BOT_TOKEN:
        return False
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=7) as response:
            response.read()
        return True
    except urllib.error.HTTPError as exc:
        logger.warning(
            "Не вдалося доставити повідомлення chat_id=%s http_status=%s",
            chat_id,
            exc.code,
        )
        return False
    except (urllib.error.URLError, TimeoutError, ValueError):
        logger.warning("Не вдалося доставити повідомлення chat_id=%s", chat_id)
        return False


def notify_new_request(booking: dict) -> bool:
    if config.ADMIN_CHAT_ID is None:
        return False
    return send_message(
        config.ADMIN_CHAT_ID,
        texts.admin_new_request_text(booking),
        _webapp_markup(),
    )


def notify_client_status(booking: dict, status: str) -> bool:
    return send_message(
        booking.get("user_id"),
        texts.client_status_text(booking, status),
        _webapp_markup(),
    )


def notify_admin_cancelled(booking: dict) -> bool:
    if config.ADMIN_CHAT_ID is None:
        return False
    return send_message(
        config.ADMIN_CHAT_ID,
        texts.admin_client_cancelled_text(booking),
        _webapp_markup(),
    )
