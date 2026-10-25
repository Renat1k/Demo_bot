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
BTN_VIEW_REQUEST = "📄 Переглянути заявку"
BTN_CONFIRM_BOOKING = "✅ Підтвердити запис"
BTN_MASTER_ACTIONS = "🛠 Дії майстра"
BTN_MASTER_CONFIRM = "✅ Підтвердити"
BTN_MASTER_REJECT = "❌ Відхилити"
BTN_MASTER_RESCHEDULE = "🕒 Запропонувати інший час"

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
    "Інтерфейс вибору послуги, дати й часу вже підготовлено."
)

RECORDS_STUB = (
    "📋 <b>Мої записи</b>\n\n"
    "🚧 Онлайн-запис ще в розробці.\n\n"
    "Інтерфейс перегляду заявки вже підготовлено."
)

BOOKING_SERVICE_TITLE = (
    "💇‍♀️ <b>Оберіть послугу</b>\n\n"
    "Натисніть на потрібну послугу, щоб перейти до вибору дати."
)

BOOKING_DATE_TITLE = (
    "📅 <b>Оберіть дату</b>\n\n"
    "Доступні дати (демо):"
)

BOOKING_TIME_TITLE = (
    "🕘 <b>Оберіть час</b>\n\n"
    "Доступні слоти (демо):"
)

DEMO_NOTICE = "🚧 Демонстраційний інтерфейс. Дані поки не зберігаються."

MASTER_ACTIONS_TITLE = (
    "🛠 <b>Дії майстра</b>\n\n"
    "Оберіть, що зробити із заявкою.\n\n"
    f"{DEMO_NOTICE}"
)

ADMIN_PANEL = "⚙️ <b>Адмін-панель</b>\n\nОберіть потрібний розділ:"

ADMIN_REQUESTS = (
    "📋 <b>Заявки</b>\n\n"
    "🚧 Розділ у розробці.\n\n"
    "Інтерфейс перегляду заявки та дій майстра вже підготовлено."
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


def service_button_label(name: str, price: str) -> str:
    return f"{name} · {price}"


def booking_summary_text(
    service: str = "—",
    date: str = "—",
    time: str = "—",
) -> str:
    return (
        "📄 <b>Перевірте заявку</b>\n\n"
        f"<b>Послуга:</b> {escape(service)}\n"
        f"<b>Дата:</b> {escape(date)}\n"
        f"<b>Час:</b> {escape(time)}\n\n"
        f"{DEMO_NOTICE}"
    )


def request_view_text(
    request_id: str = "—",
    service: str = "—",
    date: str = "—",
    time: str = "—",
    status: str = "—",
) -> str:
    return (
        f"📄 <b>Заявка №{escape(request_id)}</b>\n\n"
        f"<b>Послуга:</b> {escape(service)}\n"
        f"<b>Бажана дата:</b> {escape(date)}\n"
        f"<b>Бажаний час:</b> {escape(time)}\n"
        f"<b>Статус:</b> {escape(status)}\n\n"
        f"{DEMO_NOTICE}"
    )


def services_text() -> str:
    lines = [
        "💇‍♀️ <b>Послуги та ціни</b>",
        "",
    ]
    lines.extend(
        f"• {escape(name)} — {escape(price)}"
        for _service_id, name, price in SERVICES
    )
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
