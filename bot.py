import logging
import threading
import time

from telegram import BotCommand, Update
from telegram.error import TelegramError
from telegram.ext import Application

from config import ADMIN_CHAT_ID, BOT_TOKEN
from database import expire_stale_holds, init_db
from handlers import register_handlers
from web import run_health_server

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    try:
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Головне меню"),
                BotCommand("menu", "Головне меню"),
                BotCommand("help", "Допомога"),
                BotCommand("admin", "Адмін-панель"),
            ]
        )
    except TelegramError:
        logger.exception("Не вдалося встановити команди бота.")

    if ADMIN_CHAT_ID is None:
        logger.warning("ADMIN_CHAT_ID не задано: адмін-панель буде недоступною.")
    else:
        logger.info("Адмін-панель увімкнено.")


def hold_cleanup_loop() -> None:
    while True:
        time.sleep(30)
        try:
            expire_stale_holds()
        except Exception:
            logger.exception("Не вдалося очистити прострочені утримання.")


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "Не задано BOT_TOKEN. Додайте змінну середовища BOT_TOKEN із токеном бота."
        )

    init_db()
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    register_handlers(application)

    threading.Thread(
        target=run_health_server,
        name="health-server",
        daemon=True,
    ).start()
    threading.Thread(
        target=hold_cleanup_loop,
        name="hold-cleanup",
        daemon=True,
    ).start()

    logger.info("Бот запускається в режимі polling.")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
