from html import escape

from config import (
    ADDRESS,
    CANCELLATION_CUTOFF_MINUTES,
    CITY_LOCATIVE,
    HOLD_TTL_SECONDS,
    INSTAGRAM_URL,
    PHONE,
    PHONE_URI,
    SALON_NAME,
    SERVICES,
    TIMEZONE,
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
BTN_CANCEL_RECORD = "❌ Скасувати запис"
BTN_CONFIRM_BOOKING = "✅ Підтвердити запис"
BTN_MASTER_ACTIONS = "🛠 Дії майстра"
BTN_MASTER_CONFIRM = "✅ Підтвердити"
BTN_MASTER_REJECT = "❌ Відхилити"
BTN_MASTER_RESCHEDULE = "🕒 Запропонувати інший час"
BTN_PREV = "◀️"
BTN_NEXT = "▶️"
BTN_FILTER_PENDING = "⏳ Очікують"
BTN_FILTER_CONFIRMED = "✅ Підтверджені"
BTN_FILTER_ALL = "📋 Усі"

START = (
    "👋 <b>Вітаю!</b>\n\n"
    f"Я бот перукарні «{escape(SALON_NAME)}» у {escape(CITY_LOCATIVE)}.\n\n"
    "Тут можна переглянути послуги й ціни, контакти та записатися онлайн.\n\n"
    "Оберіть потрібний розділ:"
)

MAIN_MENU = "🏠 <b>Головне меню</b>\n\nОберіть потрібний розділ:"

HELP = (
    "ℹ️ <b>Допомога</b>\n\n"
    "Скористайтеся кнопками меню, щоб переглянути послуги, контакти або записатися.\n\n"
    "Після вибору часу слот утримується 5 хвилин. Підтвердьте заявку, "
    "інакше він звільниться.\n"
    f"Скасувати підтверджений запис онлайн можна не пізніше ніж за "
    f"{CANCELLATION_CUTOFF_MINUTES // 60} год до початку.\n\n"
    "Якщо маєте питання, зв’яжіться з перукарнею за телефоном."
)

BOOKING_SERVICE_TITLE = (
    "💇‍♀️ <b>Оберіть послугу</b>\n\n"
    "Натисніть на потрібну послугу, щоб перейти до вибору дати."
)

BOOKING_DATE_TITLE = (
    "📅 <b>Оберіть дату</b>\n\n"
    "Доступні дати на найближчі дні:"
)

BOOKING_TIME_TITLE = (
    "🕘 <b>Оберіть час</b>\n\n"
    "Доступні слоти з урахуванням тривалості послуги:"
)

BOOKING_TIME_EMPTY = "На цю дату немає вільних слотів. Оберіть іншу дату."
BOOKING_DATE_EMPTY = "На найближчі дні немає вільних дат. Спробуйте пізніше."

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

ADMIN_PANEL = "⚙️ <b>Адмін-панель</b>\n\nОберіть потрібний розділ:"


def admin_schedule_text() -> str:
    lines = [
        "🗓 <b>Розклад</b>",
        "",
        f"<b>Години роботи:</b>\n{escape(WORKING_HOURS)}",
        "",
        "<b>Послуги та тривалість:</b>",
    ]
    for service in SERVICES:
        lines.append(
            f"• {escape(service['name'])} — {service['duration_minutes']} хв"
        )
    lines.extend(
        [
            "",
            "Демонстраційний графік із config.py. "
            "Керування графіком з’явиться в наступній версії.",
        ]
    )
    return "\n".join(lines)


def admin_settings_text() -> str:
    return (
        "⚙️ <b>Налаштування</b>\n\n"
        f"<b>Утримання слота:</b> {HOLD_TTL_SECONDS // 60} хв\n"
        f"<b>Скасування клієнтом:</b> не пізніше ніж за "
        f"{CANCELLATION_CUTOFF_MINUTES // 60} год\n"
        f"<b>Часовий пояс:</b> {escape(TIMEZONE)}\n\n"
        "Зміна цих параметрів виконується в config.py."
    )

NO_ACCESS = "⛔ Доступ лише для адміністратора."
ERROR = "😔 Сталася помилка. Спробуйте ще раз трохи пізніше."
UNKNOWN_CALLBACK = "Дія недоступна. Скористайтеся меню."

ALERT_SELECT_SERVICE = "Спочатку оберіть послугу."
ALERT_SELECT_DATE = "Спочатку оберіть дату."
ALERT_SERVICE_NOT_FOUND = "Послугу не знайдено. Оберіть ще раз."
ALERT_DATE_UNAVAILABLE = "На цю дату вже немає вільних слотів. Оберіть іншу."
ALERT_TIME_NOT_FOUND = "Час недоступний. Оберіть ще раз."
ALERT_REQUEST_NOT_FOUND = "Заявку не знайдено."
ALERT_SLOT_TAKEN = "Цей час уже зайнятий. Оберіть інший."
ALERT_HOLD_EXPIRED = "Утримання вже неактивне. Оберіть слот ще раз."
ALERT_BOOKING_PROCESSED = "Заявку вже оброблено або вона недоступна."
ALERT_CANCEL_UNAVAILABLE = (
    "Запис не можна скасувати онлайн: він уже почався, "
    f"до нього менше {CANCELLATION_CUTOFF_MINUTES // 60} год. "
    "Зателефонуйте в салон."
)
ALERT_CANCEL_FORBIDDEN = "Скасувати можна лише власний запис."

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


def service_button_label(name: str, price: str, duration_minutes: int) -> str:
    return f"{name} · {price} · {duration_minutes} хв"


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
    price: str | None = None,
    duration_minutes: int | None = None,
) -> str:
    text = (
        "📄 <b>Перевірте заявку</b>\n\n"
        f"<b>Послуга:</b> {escape(service)}\n"
        f"<b>Дата:</b> {escape(date)}\n"
        f"<b>Час:</b> {escape(time)}"
    )
    if duration_minutes is not None:
        text += f"\n<b>Тривалість:</b> {duration_minutes} хв"
    if price:
        text += f"\n<b>Ціна:</b> {escape(price)}"
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
    price: str | None = None,
    duration_minutes: int | None = None,
    client: str | None = None,
) -> str:
    lines = [
        f"📄 <b>Заявка #{escape(str(request_id))}</b>",
        "",
        f"<b>Послуга:</b> {escape(service)}",
        f"<b>Бажана дата:</b> {escape(date)}",
        f"<b>Бажаний час:</b> {escape(time)}",
    ]
    if duration_minutes is not None:
        lines.append(f"<b>Тривалість:</b> {duration_minutes} хв")
    if price:
        lines.append(f"<b>Ціна:</b> {escape(price)}")
    if client:
        lines.append(f"<b>Клієнт:</b> {escape(client)}")
    lines.append(f"<b>Статус:</b> {escape(status)}")
    return "\n".join(lines)


def services_text() -> str:
    lines = [
        "💇‍♀️ <b>Послуги та ціни</b>",
        "",
    ]
    for service in SERVICES:
        lines.append(
            f"• <b>{escape(service['name'])}</b> — {escape(service['price'])}"
        )
        lines.append(f"  ⏱ {service['duration_minutes']} хв")
        lines.append(f"  {escape(service['description'])}")
        lines.append("")
    lines.append("Ціни орієнтовні. Точну вартість підтвердить майстер.")
    return "\n".join(lines)


def client_label(booking: dict) -> str:
    username = (booking.get("username") or "").strip()
    if username:
        return f"@{username}"
    user_id = booking.get("user_id")
    return f"клієнт ID {user_id}" if user_id is not None else "клієнт"


def _booking_details(booking: dict) -> list[str]:
    lines = [
        f"<b>Послуга:</b> {escape(str(booking.get('service_name', '—')))}",
        f"<b>Дата:</b> {escape(str(booking.get('date_label', '—')))}",
        f"<b>Час:</b> {escape(str(booking.get('time_label', '—')))}",
    ]
    duration = booking.get("duration_minutes")
    if duration is not None:
        lines.append(f"<b>Тривалість:</b> {duration} хв")
    price = booking.get("price_label")
    if price:
        lines.append(f"<b>Ціна:</b> {escape(str(price))}")
    return lines


def admin_new_request_text(booking: dict) -> str:
    return "\n".join(
        [
            f"🔔 <b>Нова заявка #{booking['id']}</b>",
            "",
            *_booking_details(booking),
            f"<b>Клієнт:</b> {escape(client_label(booking))}",
            f"<b>Статус:</b> {escape(booking_status_label(booking['status']))}",
            "",
            "Відкрийте заявку, щоб підтвердити або відхилити її.",
        ]
    )


def client_status_text(booking: dict, status: str) -> str:
    if status == "confirmed":
        title = "✅ <b>Запис підтверджено</b>"
        footer = "Чекаємо на вас у салоні."
    elif status == "rejected":
        title = "❌ <b>Заявку відхилено</b>"
        footer = "Оберіть інший час у меню «Записатися»."
    else:
        title = "🚫 <b>Запис скасовано</b>"
        footer = "Сподіваємося побачити вас іншим разом."
    return "\n".join(
        [
            title,
            "",
            f"<b>Заявка:</b> #{booking['id']}",
            *_booking_details(booking),
            f"<b>Статус:</b> {escape(booking_status_label(status))}",
            "",
            footer,
        ]
    )


def admin_client_cancelled_text(booking: dict) -> str:
    return "\n".join(
        [
            f"🚫 <b>Клієнт скасував запис #{booking['id']}</b>",
            "",
            *_booking_details(booking),
            f"<b>Клієнт:</b> {escape(client_label(booking))}",
            "",
            "Слот звільнено для інших клієнтів.",
        ]
    )


ADMIN_FILTER_LABELS = {
    "pending": BTN_FILTER_PENDING,
    "confirmed": BTN_FILTER_CONFIRMED,
    "all": BTN_FILTER_ALL,
}


def admin_requests_title(filter_key: str, total: int, page: int, pages: int) -> str:
    label = ADMIN_FILTER_LABELS.get(filter_key, filter_key)
    suffix = f" · стор. {page}/{pages}" if pages > 1 else ""
    return (
        "📋 <b>Заявки</b>\n\n"
        f"Фільтр: {label}{suffix}\n"
        f"Усього: {total}."
    )


def admin_requests_empty(filter_key: str) -> str:
    label = ADMIN_FILTER_LABELS.get(filter_key, filter_key)
    return f"📋 <b>Заявки</b>\n\nЗа фільтром «{label}» заявок немає."


def contacts_text() -> str:
    return (
        "📍 <b>Адреса та контакти</b>\n\n"
        f"🏠 {escape(ADDRESS)}\n"
        f"🕘 {escape(WORKING_HOURS)}\n"
        f"📞 <a href=\"{PHONE_URI}\">{escape(PHONE)}</a>\n"
        f"📸 <a href=\"{INSTAGRAM_URL}\">Instagram</a>\n\n"
        "Чекаємо на вас!"
    )
