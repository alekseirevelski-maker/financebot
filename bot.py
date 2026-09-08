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
from middlewares.throttling import ThrottleMiddleware
from handlers import start, survey, plan, tracker, reminders, wisdom, compound, profile, photo, recurring, savings, budget, analytics, reports, forecast
from services.scheduler_jobs import check_reminders


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан!")
        return

    # Set proxy env vars (same pattern as working bots)
    if PROXY_URL:
        os.environ["http_proxy"] = PROXY_URL
        os.environ["https_proxy"] = PROXY_URL
        logger.info("Прокси: %s", PROXY_URL)

    await init_db()
    logger.info("БД инициализирована")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(ThrottleMiddleware(limit=0.5))

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

    logger.info("Бот запущен в режиме polling")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, "interval", minutes=5, args=[bot])
    scheduler.start()
    logger.info("APScheduler запущен — напоминания каждые 5 мин")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
    asyncio.run(main())
