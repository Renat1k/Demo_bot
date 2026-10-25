from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config import SERVICES, WEBAPP_URL
import texts

CB_MAIN = "nav:main"
CB_BOOK = "user:book"
CB_SERVICES = "user:services"
CB_RECORDS = "user:records"
CB_CONTACTS = "user:contacts"

CB_ADMIN = "admin:panel"
CB_ADMIN_REQUESTS = "admin:requests"
CB_ADMIN_REQUESTS_QUERY_PREFIX = "admin:requests:"
CB_ADMIN_SCHEDULE = "admin:schedule"
CB_ADMIN_SETTINGS = "admin:settings"

CB_BOOK_DATES = "booking:dates"
CB_BOOK_TIMES = "booking:times"
CB_BOOK_CONFIRM = "booking:confirm"
CB_BOOK_CANCEL = "booking:cancel"
CB_BOOK_HOME = "booking:home"

CB_SERVICE_PREFIX = "booking:service:"
CB_DATE_PREFIX = "booking:date:"
CB_TIME_PREFIX = "booking:time:"
CB_REQUEST_VIEW_PREFIX = "request:view:"
CB_CANCEL_REQUEST_PREFIX = "cancel:request:"
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
    if WEBAPP_URL.startswith("https://"):
        rows.append(
            [
                InlineKeyboardButton(
                    texts.BTN_WEBAPP,
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        )
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
                texts.service_button_label(
                    service["name"],
                    service["price"],
                    service["duration_minutes"],
                ),
                callback_data=f"{CB_SERVICE_PREFIX}{service['id']}",
            )
        ]
        for service in SERVICES
    ]
    rows.append([InlineKeyboardButton(texts.BTN_HOME, callback_data=CB_MAIN)])
    return InlineKeyboardMarkup(rows)


def date_selection_keyboard(dates: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_DATE_PREFIX}{date_id}",
            )
        ]
        for date_id, label in dates
    ]
    rows.extend(_navigation_rows(CB_BOOK))
    return InlineKeyboardMarkup(rows)


def time_selection_keyboard(times: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_TIME_PREFIX}{time_id}",
            )
            for time_id, label in times[index : index + 3]
        ]
        for index in range(0, len(times), 3)
    ]
    rows.extend(_navigation_rows(CB_BOOK_DATES))
    return InlineKeyboardMarkup(rows)


def booking_summary_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    texts.BTN_CONFIRM_BOOKING,
                    callback_data=CB_BOOK_CONFIRM,
                )
            ],
            [InlineKeyboardButton(texts.BTN_BACK, callback_data=CB_BOOK_TIMES)],
            [InlineKeyboardButton(texts.BTN_CANCEL_BOOKING, callback_data=CB_BOOK_CANCEL)],
            [InlineKeyboardButton(texts.BTN_HOME, callback_data=CB_BOOK_HOME)],
        ]
    )


def booking_success_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(texts.BTN_RECORDS, callback_data=CB_RECORDS)],
            [InlineKeyboardButton(texts.BTN_HOME, callback_data=CB_MAIN)],
        ]
    )


def request_list_keyboard(
    requests: list[dict] | None = None,
    back_callback: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                texts.request_button_label(
                    booking["id"],
                    booking["service_name"],
                    booking["date_label"],
                    booking["time_label"],
                ),
                callback_data=f"{CB_REQUEST_VIEW_PREFIX}{booking['id']}",
            )
        ]
        for booking in (requests or [])
    ]
    if back_callback is None:
        rows.append([InlineKeyboardButton(texts.BTN_HOME, callback_data=CB_MAIN)])
    else:
        rows.extend(_navigation_rows(back_callback))
    return InlineKeyboardMarkup(rows)


def request_view_keyboard(
    request_id: int | str,
    back_callback: str = CB_RECORDS,
    master: bool = False,
    cancel: bool = False,
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
    if cancel:
        rows.append(
            [
                InlineKeyboardButton(
                    texts.BTN_CANCEL_RECORD,
                    callback_data=f"{CB_CANCEL_REQUEST_PREFIX}{request_id}",
                )
            ]
        )
    rows.extend(_navigation_rows(back_callback))
    return InlineKeyboardMarkup(rows)


def admin_requests_keyboard(
    requests: list[dict],
    filter_key: str,
    page: int,
    pages: int,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                texts.request_button_label(
                    booking["id"],
                    booking["service_name"],
                    booking["date_label"],
                    booking["time_label"],
                ),
                callback_data=f"{CB_REQUEST_VIEW_PREFIX}{booking['id']}",
            )
        ]
        for booking in requests
    ]
    filters = [
        ("pending", texts.BTN_FILTER_PENDING),
        ("confirmed", texts.BTN_FILTER_CONFIRMED),
        ("all", texts.BTN_FILTER_ALL),
    ]
    rows.append(
        [
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_ADMIN_REQUESTS_QUERY_PREFIX}{key}:1",
            )
            for key, label in filters
            if key != filter_key
        ]
    )
    if pages > 1:
        navigation = []
        if page > 1:
            navigation.append(
                InlineKeyboardButton(
                    texts.BTN_PREV,
                    callback_data=f"{CB_ADMIN_REQUESTS_QUERY_PREFIX}{filter_key}:{page - 1}",
                )
            )
        navigation.append(
            InlineKeyboardButton(
                f"{page}/{pages}",
                callback_data=f"{CB_ADMIN_REQUESTS_QUERY_PREFIX}{filter_key}:{page}",
            )
        )
        if page < pages:
            navigation.append(
                InlineKeyboardButton(
                    texts.BTN_NEXT,
                    callback_data=f"{CB_ADMIN_REQUESTS_QUERY_PREFIX}{filter_key}:{page + 1}",
                )
            )
        rows.append(navigation)
    rows.extend(_navigation_rows(CB_ADMIN))
    return InlineKeyboardMarkup(rows)


def master_actions_keyboard(request_id: int | str) -> InlineKeyboardMarkup:
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
