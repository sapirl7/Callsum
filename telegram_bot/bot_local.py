<![CDATA[# -*- coding: utf-8 -*-
"""
Local bot version for testing (polling mode).
For development and debugging before deploying to AWS Lambda.
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
    """Start the bot in polling mode."""
    logger.info("Starting bot in polling mode...")

    application = build_application()

    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    logger.info("Bot started! Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
]]>
