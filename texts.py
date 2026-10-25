from html import escape

from config import (
    ADDRESS,
    CITY_LOCATIVE,
    INSTAGRAM_URL,
    PHONE,
    PHONE_URI,
    SALON_NAME,
    SERVICES,
    WORKING_HOURS,
)

BTN_BOOK = "📅 Записатися"
BTN_SERVICES = "💇‍♀️ Послуги та ціни"
BTN_RECORDS = "📋 Мої записи"
BTN_CONTACTS = "📍 Адреса та контакти"
BTN_ADMIN = "⚙️ Адмін-панель"
BTN_REQUESTS = "📋 Заявки"
BTN_SCHEDULE = "🗓 Розклад"
BTN_SETTINGS = "⚙️ Налаштування"
BTN_BACK = "⬅️ Назад"
BTN_HOME = "🏠 Головне меню"

START = (
    "👋 <b>Вітаю!</b>\n\n"
    f"Я бот перукарні «{escape(SALON_NAME)}» у {escape(CITY_LOCATIVE)}.\n\n"
    "Тут можна переглянути послуги й ціни, контакти та незабаром — записатися онлайн.\n\n"
    "Оберіть потрібний розділ:"
)

MAIN_MENU = "🏠 <b>Головне меню</b>\n\nОберіть потрібний розділ:"

HELP = (
    "ℹ️ <b>Допомога</b>\n\n"
    "Скористайтеся кнопками меню, щоб переглянути потрібний розділ.\n\n"
    "Якщо маєте питання, зв’яжіться з перукарнею за телефоном."
)

BOOKING_STUB = (
    "📅 <b>Запис</b>\n\n"
    "🚧 Онлайн-запис ще в розробці.\n\n"
    "Незабаром тут можна буде обрати послугу, майстра та зручний час."
)

RECORDS_STUB = (
    "📋 <b>Мої записи</b>\n\n"
    "🚧 Онлайн-запис ще в розробці.\n\n"
    "Тут з’являться ваші майбутні записи."
)

ADMIN_PANEL = "⚙️ <b>Адмін-панель</b>\n\nОберіть потрібний розділ:"

ADMIN_REQUESTS = (
    "📋 <b>Заявки</b>\n\n"
    "🚧 Розділ у розробці.\n\n"
    "Тут з’являться заявки клієнтів."
)

ADMIN_SCHEDULE = (
    "🗓 <b>Розклад</b>\n\n"
    "🚧 Розділ у розробці.\n\n"
    "Тут можна буде керувати робочим графіком і записами."
)

ADMIN_SETTINGS = (
    "⚙️ <b>Налаштування</b>\n\n"
    "🚧 Розділ у розробці.\n\n"
    "Тут будуть налаштування бота та перукарні."
)

NO_ACCESS = "⛔ Доступ лише для адміністратора."
ERROR = "😔 Сталася помилка. Спробуйте ще раз трохи пізніше."


def services_text() -> str:
    lines = [
        "💇‍♀️ <b>Послуги та ціни</b>",
        "",
    ]
    lines.extend(f"• {escape(name)} — {escape(price)}" for name, price in SERVICES)
    lines.extend(
        [
            "",
            "Ціни орієнтовні. Точну вартість підтвердить майстер.",
        ]
    )
    return "\n".join(lines)


def contacts_text() -> str:
    return (
        "📍 <b>Адреса та контакти</b>\n\n"
        f"🏠 {escape(ADDRESS)}\n"
        f"🕘 {escape(WORKING_HOURS)}\n"
        f"📞 <a href=\"{PHONE_URI}\">{escape(PHONE)}</a>\n"
        f"📸 <a href=\"{INSTAGRAM_URL}\">Instagram</a>\n\n"
        "Чекаємо на вас!"
    )
