import asyncio
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from config import BOT_TOKEN, PROXY_URL
from db.engine import init_db
from middlewares.access import AccessMiddleware
from middlewares.throttling import ThrottleMiddleware
from handlers import start, survey, plan, tracker, reminders, wisdom, compound, profile, photo, recurring, savings, budget, analytics, reports, forecast
from services.scheduler_jobs import check_reminders


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан!")
        return

    await init_db()
    logger.info("БД инициализирована")

    # Bot creation with proxy support
    if PROXY_URL:
        if PROXY_URL.startswith("socks5"):
            try:
                from aiohttp_socks import SocksConnector, SocksVer
                host = PROXY_URL.split("//")[1].split(":")[0]
                port = int(PROXY_URL.split(":")[-1].split("/")[0])
                connector = SocksConnector(
                    socks_ver=SocksVer.SOCKS5,
                    host=host,
                    port=port,
                )
                session = AiohttpSession(connector=connector)
                bot = Bot(token=BOT_TOKEN, session=session)
                logger.info("SOCKS5 proxy: %s", PROXY_URL)
            except ImportError:
                logger.warning("aiohttp-socks not installed, using env vars for proxy")
                os.environ["http_proxy"] = PROXY_URL
                os.environ["https_proxy"] = PROXY_URL
                bot = Bot(token=BOT_TOKEN)
        else:
            session = AiohttpSession(proxy=PROXY_URL)
            bot = Bot(token=BOT_TOKEN, session=session)
            logger.info("HTTP proxy: %s", PROXY_URL)
    else:
        bot = Bot(token=BOT_TOKEN)
        logger.info("No proxy — direct connection")

    dp = Dispatcher(storage=MemoryStorage())

    # Access control — BEFORE everything else
    dp.message.outer_middleware(AccessMiddleware())
    dp.callback_query.outer_middleware(AccessMiddleware())

    dp.message.middleware(ThrottleMiddleware(limit=1.0))

    dp.include_routers(
        start.router,
        survey.router,
        plan.router,
        tracker.router,
        reminders.router,
        wisdom.router,
        compound.router,
        profile.router,
        photo.router,
        recurring.router,
        savings.router,
        budget.router,
        analytics.router,
        reports.router,
        forecast.router,
    )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, "interval", minutes=5, args=[bot])
    scheduler.start()
    logger.info("APScheduler запущен — напоминания каждые 5 мин")

    logger.info("Бот запущен в режиме polling")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=True)
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
    asyncio.run(main())
