from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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


def admin_section_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(texts.BTN_BACK, callback_data=CB_ADMIN)],
            [InlineKeyboardButton(texts.BTN_HOME, callback_data=CB_MAIN)],
        ]
    )
