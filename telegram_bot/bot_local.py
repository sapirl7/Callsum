# -*- coding: utf-8 -*-
"""
Локальная версия бота для тестирования (polling режим).
Для разработки и отладки перед деплоем на AWS Lambda.
"""

import asyncio
import logging

from telegram import Update

from bot import build_application


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


async def main():
    """Запуск бота в polling режиме."""
    logger.info("Запуск бота в режиме polling...")

    application = build_application()

    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    logger.info("Бот запущен! Нажмите Ctrl+C для остановки.")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
