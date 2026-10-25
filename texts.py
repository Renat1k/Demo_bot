from html import escape

from config import (
    ADDRESS,
    CITY_LOCATIVE,
    HOLD_TTL_SECONDS,
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
BTN_CANCEL_BOOKING = "❌ Скасувати вибір"
BTN_CONFIRM_BOOKING = "✅ Підтвердити запис"
BTN_MASTER_ACTIONS = "🛠 Дії майстра"
BTN_MASTER_CONFIRM = "✅ Підтвердити"
BTN_MASTER_REJECT = "❌ Відхилити"
BTN_MASTER_RESCHEDULE = "🕒 Запропонувати інший час"

START = (
    "👋 <b>Вітаю!</b>\n\n"
    f"Я бот перукарні «{escape(SALON_NAME)}» у {escape(CITY_LOCATIVE)}.\n\n"
    "Тут можна переглянути послуги й ціни, контакти та записатися онлайн.\n\n"
    "Оберіть потрібний розділ:"
)

MAIN_MENU = "🏠 <b>Головне меню</b>\n\nОберіть потрібний розділ:"

HELP = (
    "ℹ️ <b>Допомога</b>\n\n"
    "Скористайтеся кнопками меню, щоб переглянути потрібний розділ.\n\n"
    "Якщо маєте питання, зв’яжіться з перукарнею за телефоном."
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

BOOKING_TIME_EMPTY = "На цю дату немає вільних слотів. Оберіть іншу дату."

MASTER_ACTIONS_TITLE = (
    "🛠 <b>Дії майстра</b>\n\n"
    "Оберіть, що зробити із заявкою."
)

MASTER_CONFIRMED = (
    "✅ <b>Заявку підтверджено</b>\n\n"
    "Запис підтверджено. Слот залишається зайнятим."
)

MASTER_REJECTED = (
    "❌ <b>Заявку відхилено</b>\n\n"
    "Слот звільнено для інших клієнтів."
)

MASTER_RESCHEDULE_STUB = (
    "🕒 <b>Інший час</b>\n\n"
    "Функція узгодження іншого часу ще в розробці. "
    "Заявка залишається в очікуванні."
)

RECORDS_TITLE = "📋 <b>Мої записи</b>\n\nОберіть заявку:"
RECORDS_EMPTY = "📋 <b>Мої записи</b>\n\nУ вас поки немає заявок."

ADMIN_REQUESTS_TITLE = "📋 <b>Заявки</b>\n\nОберіть заявку:"
ADMIN_REQUESTS_EMPTY = "📋 <b>Заявки</b>\n\nНових заявок немає."

ADMIN_PANEL = "⚙️ <b>Адмін-панель</b>\n\nОберіть потрібний розділ:"

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
UNKNOWN_CALLBACK = "Дія недоступна. Скористайтеся меню."

ALERT_SELECT_SERVICE = "Спочатку оберіть послугу."
ALERT_SELECT_DATE = "Спочатку оберіть дату."
ALERT_SERVICE_NOT_FOUND = "Послугу не знайдено. Оберіть ще раз."
ALERT_DATE_NOT_FOUND = "Дату не знайдено. Оберіть ще раз."
ALERT_TIME_NOT_FOUND = "Час недоступний. Оберіть ще раз."
ALERT_REQUEST_NOT_FOUND = "Заявку не знайдено."
ALERT_SLOT_TAKEN = "Цей час уже зайнятий. Оберіть інший."
ALERT_HOLD_EXPIRED = "Утримання вже неактивне. Оберіть слот ще раз."
ALERT_BOOKING_PROCESSED = "Заявку вже оброблено або вона недоступна."

BOOKING_STATUS_LABELS = {
    "held": "Утримується",
    "pending": "Очікує підтвердження майстра",
    "confirmed": "Підтверджена",
    "rejected": "Відхилена",
    "cancelled": "Скасована",
    "expired": "Термін утримання минув",
}


def booking_status_label(status: str) -> str:
    return BOOKING_STATUS_LABELS.get(status, "—")


def service_button_label(name: str, price: str) -> str:
    return f"{name} · {price}"


def request_button_label(
    booking_id: int,
    service_name: str,
    date_label: str,
    time_label: str,
) -> str:
    return f"#{booking_id} · {service_name} · {date_label}, {time_label}"


def booking_summary_text(
    service: str,
    date: str,
    time: str,
    hold_until: str | None = None,
) -> str:
    text = (
        "📄 <b>Перевірте заявку</b>\n\n"
        f"<b>Послуга:</b> {escape(service)}\n"
        f"<b>Дата:</b> {escape(date)}\n"
        f"<b>Час:</b> {escape(time)}"
    )
    if hold_until:
        text += (
            "\n\n⏳ Слот утримується до "
            f"<b>{escape(hold_until)}</b>. Підтвердьте заявку протягом "
            f"{HOLD_TTL_SECONDS // 60} хвилин."
        )
    return text


def booking_submitted_text(booking_id: int, status: str) -> str:
    return (
        "✅ <b>Заявку надіслано</b>\n\n"
        f"<b>Номер:</b> #{booking_id}\n"
        f"<b>Статус:</b> {escape(status)}\n\n"
        "Майстер отримає заявку та підтвердить або відхилить її."
    )


def request_view_text(
    request_id: int | str,
    service: str,
    date: str,
    time: str,
    status: str,
) -> str:
    return (
        f"📄 <b>Заявка #{escape(str(request_id))}</b>\n\n"
        f"<b>Послуга:</b> {escape(service)}\n"
        f"<b>Бажана дата:</b> {escape(date)}\n"
        f"<b>Бажаний час:</b> {escape(time)}\n"
        f"<b>Статус:</b> {escape(status)}"
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
