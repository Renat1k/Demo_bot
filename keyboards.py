from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import DEMO_DATES, DEMO_REQUEST_ID, DEMO_TIMES, SERVICES
import texts

CB_MAIN = "nav:main"
CB_BOOK = "user:book"
CB_SERVICES = "user:services"
CB_RECORDS = "user:records"
CB_CONTACTS = "user:contacts"

CB_ADMIN = "admin:panel"
CB_ADMIN_REQUESTS = "admin:requests"
CB_ADMIN_SCHEDULE = "admin:schedule"
CB_ADMIN_SETTINGS = "admin:settings"

CB_BOOK_DATES = "booking:dates"
CB_BOOK_TIMES = "booking:times"
CB_BOOK_PREVIEW = "booking:preview"
CB_BOOK_CONFIRM = "booking:confirm"

CB_SERVICE_PREFIX = "booking:service:"
CB_DATE_PREFIX = "booking:date:"
CB_TIME_PREFIX = "booking:time:"
CB_REQUEST_VIEW_PREFIX = "request:view:"
CB_MASTER_ACTIONS_PREFIX = "master:actions:"
CB_MASTER_CONFIRM_PREFIX = "master:confirm:"
CB_MASTER_REJECT_PREFIX = "master:reject:"
CB_MASTER_RESCHEDULE_PREFIX = "master:reschedule:"


def _navigation_rows(
    back_callback: str, home_callback: str = CB_MAIN
) -> list[list[InlineKeyboardButton]]:
    return [
        [InlineKeyboardButton(texts.BTN_BACK, callback_data=back_callback)],
        [InlineKeyboardButton(texts.BTN_HOME, callback_data=home_callback)],
    ]


def back_home_keyboard(back_callback: str, home_callback: str = CB_MAIN) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(_navigation_rows(back_callback, home_callback))


def main_menu_keyboard(admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(texts.BTN_BOOK, callback_data=CB_BOOK)],
        [InlineKeyboardButton(texts.BTN_SERVICES, callback_data=CB_SERVICES)],
        [InlineKeyboardButton(texts.BTN_RECORDS, callback_data=CB_RECORDS)],
        [InlineKeyboardButton(texts.BTN_CONTACTS, callback_data=CB_CONTACTS)],
    ]
    if admin:
        rows.append([InlineKeyboardButton(texts.BTN_ADMIN, callback_data=CB_ADMIN)])
    return InlineKeyboardMarkup(rows)


def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(texts.BTN_HOME, callback_data=CB_MAIN)]]
    )


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(texts.BTN_REQUESTS, callback_data=CB_ADMIN_REQUESTS),
                InlineKeyboardButton(texts.BTN_SCHEDULE, callback_data=CB_ADMIN_SCHEDULE),
            ],
            [InlineKeyboardButton(texts.BTN_SETTINGS, callback_data=CB_ADMIN_SETTINGS)],
            [InlineKeyboardButton(texts.BTN_HOME, callback_data=CB_MAIN)],
        ]
    )


def service_selection_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                texts.service_button_label(name, price),
                callback_data=f"{CB_SERVICE_PREFIX}{service_id}",
            )
        ]
        for service_id, name, price in SERVICES
    ]
    rows.append([InlineKeyboardButton(texts.BTN_HOME, callback_data=CB_MAIN)])
    return InlineKeyboardMarkup(rows)


def date_selection_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_DATE_PREFIX}{date_id}",
            )
        ]
        for date_id, label in DEMO_DATES
    ]
    rows.extend(_navigation_rows(CB_BOOK))
    return InlineKeyboardMarkup(rows)


def time_selection_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_TIME_PREFIX}{time_id}",
            )
            for time_id, label in DEMO_TIMES[index : index + 3]
        ]
        for index in range(0, len(DEMO_TIMES), 3)
    ]
    rows.extend(_navigation_rows(CB_BOOK_DATES))
    return InlineKeyboardMarkup(rows)


def booking_summary_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                texts.BTN_CONFIRM_BOOKING,
                callback_data=CB_BOOK_CONFIRM,
            )
        ]
    ]
    rows.extend(_navigation_rows(CB_BOOK_TIMES))
    return InlineKeyboardMarkup(rows)


def request_list_keyboard(
    request_id: str = DEMO_REQUEST_ID,
    back_callback: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                texts.BTN_VIEW_REQUEST,
                callback_data=f"{CB_REQUEST_VIEW_PREFIX}{request_id}",
            )
        ]
    ]
    if back_callback is None:
        rows.append([InlineKeyboardButton(texts.BTN_HOME, callback_data=CB_MAIN)])
    else:
        rows.extend(_navigation_rows(back_callback))
    return InlineKeyboardMarkup(rows)


def request_view_keyboard(
    request_id: str = DEMO_REQUEST_ID,
    back_callback: str = CB_RECORDS,
    master: bool = False,
) -> InlineKeyboardMarkup:
    rows = []
    if master:
        rows.append(
            [
                InlineKeyboardButton(
                    texts.BTN_MASTER_ACTIONS,
                    callback_data=f"{CB_MASTER_ACTIONS_PREFIX}{request_id}",
                )
            ]
        )
    rows.extend(_navigation_rows(back_callback))
    return InlineKeyboardMarkup(rows)


def master_actions_keyboard(request_id: str = DEMO_REQUEST_ID) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                texts.BTN_MASTER_CONFIRM,
                callback_data=f"{CB_MASTER_CONFIRM_PREFIX}{request_id}",
            ),
            InlineKeyboardButton(
                texts.BTN_MASTER_REJECT,
                callback_data=f"{CB_MASTER_REJECT_PREFIX}{request_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                texts.BTN_MASTER_RESCHEDULE,
                callback_data=f"{CB_MASTER_RESCHEDULE_PREFIX}{request_id}",
            )
        ],
    ]
    rows.extend(_navigation_rows(f"{CB_REQUEST_VIEW_PREFIX}{request_id}"))
    return InlineKeyboardMarkup(rows)
