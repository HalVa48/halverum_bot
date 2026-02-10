"""
Основной файл с логикой Telegram-бота для VPN-сервиса
"""

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from bot.handlers import (
    buy_subscription,
    get_vpn_config,
    my_subscription,
    show_tariffs,
    start,
)
from config import TELEGRAM_BOT_TOKEN

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Запуск бота"""
    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        CallbackQueryHandler(show_tariffs, pattern="^show_tariffs$")
    )
    application.add_handler(
        CallbackQueryHandler(buy_subscription, pattern="^buy_subscription$")
    )
    application.add_handler(
        CallbackQueryHandler(get_vpn_config, pattern="^get_vpn_config$")
    )
    application.add_handler(
        CallbackQueryHandler(my_subscription, pattern="^my_subscription$")
    )
    application.add_handler(CallbackQueryHandler(start, pattern="^back_to_main$"))

    # Запуск бота
    logger.info("Запуск VPN-бота...")
    application.run_polling()


if __name__ == "__main__":
    main()
