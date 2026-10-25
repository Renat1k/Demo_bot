from telegram.ext import Application, CallbackQueryHandler

from . import common, user, admin


def register_handlers(application: Application) -> None:
    common.register(application)
    user.register(application)
    admin.register(application)
    application.add_handler(CallbackQueryHandler(common.unknown_callback))
