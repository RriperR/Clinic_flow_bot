import asyncio

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from app.container import build_container
from app.infrastructure.db.models import async_main
from app.handlers.register_handlers import create_register_router
from app.handlers.survey_handlers import create_survey_router
from app.handlers.admin_handlers import create_admin_router
from app.handlers.shift_handlers import create_shift_router
from app.handlers.shift_admin_handlers import create_shift_admin_router
from app.handlers.moves_handlers import create_moves_router
from app.handlers.instrument_transfer_handlers import create_instrument_transfer_router
from app.handlers.admin_panel_handlers import create_admin_panel_router
from app.logger import setup_logger


async def main():
    load_dotenv()
    container = build_container()
    settings = container.settings

    logger = setup_logger("bot", "bot.log")

    bot = Bot(token=settings.bot.token)
    dp = Dispatcher()

    await async_main()

    dp.include_router(create_admin_router(container.admin_sync))
    dp.include_router(create_register_router(container.registration))
    dp.include_router(create_survey_router(container.survey_flow))
    dp.include_router(create_shift_router(container.shift_service))
    dp.include_router(create_shift_admin_router(container.shift_admin, container.admin_access))
    dp.include_router(create_moves_router(container.instrument_admin))
    dp.include_router(create_instrument_transfer_router(container.instrument_transfer))
    dp.include_router(
        create_admin_panel_router(container.instrument_admin, container.admin_access)
    )

    scheduler = AsyncIOScheduler()
    # scheduler.add_job(container.admin_sync.sync_pairs, "cron", hour=19, minute=50)
    scheduler.add_job(container.admin_sync.sync_workers, "cron", hour=5, minute=55)
    scheduler.add_job(container.admin_sync.sync_shifts, "cron", hour=6, minute=0)
    # scheduler.add_job(container.scheduler.send_surveys, "cron", hour=20, minute=0, args=[bot, dp])
    # scheduler.add_job(container.admin_sync.export_answers, "cron", day_of_week="sun", hour=23, minute=0)
    scheduler.add_job(container.admin_sync.export_shifts, "cron", hour=23, minute=5)
    # scheduler.add_job(container.reports.send_monthly_reports, "cron", day=1, hour=16, minute=38, args=[bot])
    scheduler.start()
    logger.info("Scheduler started with jobs: %s", scheduler.get_jobs())

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown")
