from telegram.ext import Application

from . import common, user, admin


def register_handlers(application: Application) -> None:
    common.register(application)
    user.register(application)
    admin.register(application)
