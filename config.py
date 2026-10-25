import logging
import os

logger = logging.getLogger(__name__)


def _read_admin_chat_id() -> int | None:
    raw = os.environ.get("ADMIN_CHAT_ID", "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        logger.warning("ADMIN_CHAT_ID має бути цілим числом. Адмін-панель вимкнено.")
        return None


def _read_port() -> int:
    raw = os.environ.get("PORT", "10000").strip()
    try:
        port = int(raw)
        if 0 < port < 65536:
            return port
    except ValueError:
        pass
    logger.warning("Некоректний PORT=%s. Використовую 10000.", raw)
    return 10000


BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = _read_admin_chat_id()
PORT = _read_port()

SALON_NAME = "Найкраща"
CITY = "Київ"
CITY_LOCATIVE = "Києві"
ADDRESS = "Київ, вул. Прикладна, 1 (демо)"
PHONE = "+380 (67) 000-00-00"
PHONE_URI = "tel:+380670000000"
INSTAGRAM_URL = "https://instagram.com/naikrashcha_demo"
WORKING_HOURS = "Пн–Сб: 09:00–20:00\nНд: 10:00–18:00"

SERVICES = (
    ("haircut", "Стрижка", "від 500 грн"),
    ("styling", "Укладка", "від 400 грн"),
    ("coloring", "Фарбування", "від 1 200 грн"),
    ("care", "Догляд за волоссям", "від 700 грн"),
)

DEMO_DATES = (
    ("2026-10-27", "27 жовтня"),
    ("2026-10-28", "28 жовтня"),
    ("2026-10-29", "29 жовтня"),
    ("2026-10-30", "30 жовтня"),
    ("2026-10-31", "31 жовтня"),
)

DEMO_TIMES = (
    ("t1", "10:00"),
    ("t2", "12:00"),
    ("t3", "14:00"),
    ("t4", "16:00"),
    ("t5", "18:00"),
)

DEMO_REQUEST_ID = "demo"


def is_admin(user_id: int | None) -> bool:
    return bool(ADMIN_CHAT_ID) and user_id == ADMIN_CHAT_ID
