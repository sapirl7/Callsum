# -*- coding: utf-8 -*-
"""
Локальная версия бота для тестирования (polling режим).
Для разработки и отладки перед деплоем на AWS Lambda.
"""
import asyncio
from telegram.ext import Application
from bot import (
    start_command,
    help_command,
    status_command,
    voice_handler,
    BOT_TOKEN
)
from telegram.ext import filters, CommandHandler, MessageHandler
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


async def main():
    """Запуск бота в polling режиме"""
    logger.info("Запуск бота в режиме polling...")

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.VOICE, voice_handler))

    # Запускаем polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    logger.info("Бот запущен! Нажмите Ctrl+C для остановки.")

    # Ждем
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Остановка бота...")

    # Останавливаем
    await application.updater.stop()
    await application.stop()
    await application.shutdown()


if __name__ == '__main__':
    from telegram import Update
    asyncio.run(main())
