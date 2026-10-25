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
DB_PATH = os.environ.get("DB_PATH", "bot.db").strip() or "bot.db"
HOLD_TTL_SECONDS = 300
TIMEZONE = "Europe/Kyiv"
BOOKING_FLOW_KEY = "booking_flow"

SALON_NAME = "Найкраща"
CITY = "Київ"
CITY_LOCATIVE = "Києві"
ADDRESS = "Київ, вул. Прикладна, 1 (демо)"
PHONE = "+380 (67) 000-00-00"
PHONE_URI = "tel:+380670000000"
INSTAGRAM_URL = "https://instagram.com/naikrashcha_demo"
WORKING_HOURS = "Пн–Сб: 09:00–20:00\nНд: 10:00–18:00\nОбід: 13:00–14:00"

SERVICES = (
    {
        "id": "haircut",
        "name": "Стрижка",
        "price": "від 500 грн",
        "duration_minutes": 60,
        "description": "Стрижка з урахуванням форми обличчя та типу волосся.",
    },
    {
        "id": "styling",
        "name": "Укладка",
        "price": "від 400 грн",
        "duration_minutes": 45,
        "description": "Укладка на повсякдення або подію.",
    },
    {
        "id": "coloring",
        "name": "Фарбування",
        "price": "від 1 200 грн",
        "duration_minutes": 120,
        "description": "Фарбування з підбором відтінку та доглядом після.",
    },
    {
        "id": "care",
        "name": "Догляд за волоссям",
        "price": "від 700 грн",
        "duration_minutes": 60,
        "description": "Живлення, зволоження та відновлення структури волосся.",
    },
)
SERVICES_BY_ID = {service["id"]: service for service in SERVICES}

# Демонстраційний графік: його легко замінити реальним графіком салону.
# Ключ — weekday: 0 = понеділок, 6 = неділя.
WORKING_HOURS_BY_WEEKDAY = {
    0: ("09:00", "20:00"),
    1: ("09:00", "20:00"),
    2: ("09:00", "20:00"),
    3: ("09:00", "20:00"),
    4: ("09:00", "20:00"),
    5: ("09:00", "20:00"),
    6: ("10:00", "18:00"),
}
BREAKS = ((13 * 60, 14 * 60),)
SLOT_STEP_MINUTES = 30
BOOKING_DAYS_AHEAD = 14
CANCELLATION_CUTOFF_MINUTES = 120



def is_admin(user_id: int | None) -> bool:
    return bool(ADMIN_CHAT_ID) and user_id == ADMIN_CHAT_ID
