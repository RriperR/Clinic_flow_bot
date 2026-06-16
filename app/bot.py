import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ChatType
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.container import build_container
from app.error_handlers import GlobalErrorHandler
from app.handlers.admin_handlers import create_admin_router
from app.handlers.admin_panel_handlers import create_admin_panel_router
from app.handlers.instrument_transfer_handlers import create_instrument_transfer_router
from app.handlers.knowledge_handlers import create_knowledge_router
from app.handlers.moves_handlers import create_moves_router
from app.handlers.register_handlers import create_register_router
from app.handlers.report_handlers import create_report_router
from app.handlers.shift_admin_handlers import create_shift_admin_router
from app.handlers.shift_handlers import create_shift_router
from app.handlers.survey_handlers import create_survey_router
from app.infrastructure.db.models import async_main
from app.logger import setup_logger, setup_telegram_logging, shutdown_telegram_logging
from app.logging_middleware import UserActionLoggingMiddleware


async def main():
    container = build_container()
    settings = container.settings

    logger = setup_logger("bot", "bot.log")

    bot = Bot(token=settings.bot.token)
    setup_telegram_logging(bot, settings.bot.report_chat_id)

    dp = Dispatcher()
    dp.message.filter(lambda message: message.chat.type == ChatType.PRIVATE)
    dp.callback_query.filter(
        lambda callback: callback.message and callback.message.chat.type == ChatType.PRIVATE
    )
    action_logging = UserActionLoggingMiddleware(container.worker_repo)
    dp.message.outer_middleware(action_logging)
    dp.callback_query.outer_middleware(action_logging)
    dp.errors.register(GlobalErrorHandler(container.worker_repo))

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="зарегистрироваться"),
            BotCommand(command="base", description="открыть базу знаний"),
            BotCommand(command="shift", description="выбрать смену"),
            BotCommand(command="report", description="посмотреть отчёт"),
            BotCommand(command="move_instrument", description="перенести инструмент"),
            BotCommand(command="moves", description="история перемещений"),
        ]
    )

    await async_main()

    dp.include_router(create_admin_router(container.admin_sync))
    dp.include_router(create_register_router(container.registration))
    dp.include_router(create_survey_router(container.survey_flow))
    dp.include_router(create_shift_router(container.shift_service, container.worker_report))
    dp.include_router(create_report_router(container.worker_report))
    dp.include_router(create_shift_admin_router(container.shift_admin, container.admin_access))
    dp.include_router(create_moves_router(container.instrument_admin))
    dp.include_router(create_instrument_transfer_router(container.instrument_transfer))
    dp.include_router(create_admin_panel_router(container.instrument_admin, container.admin_access))
    dp.include_router(create_knowledge_router(container.knowledge_base))

    scheduler = AsyncIOScheduler()
    # scheduler.add_job(container.admin_sync.sync_pairs, "cron", hour=19, minute=50)
    scheduler.add_job(container.admin_sync.sync_knowledge_base, "cron", hour=5, minute=50)
    scheduler.add_job(container.admin_sync.sync_workers, "cron", hour=5, minute=55)
    scheduler.add_job(container.admin_sync.sync_shifts, "cron", hour=6, minute=0)
    # scheduler.add_job(container.scheduler.send_surveys, "cron", hour=20, minute=0, args=[bot, dp])
    # scheduler.add_job(container.admin_sync.export_answers, "cron", day_of_week="sun", hour=23, minute=0)
    scheduler.add_job(container.admin_sync.export_shifts, "cron", hour=4, minute=0)
    # scheduler.add_job(container.reports.send_monthly_reports, "cron", day=1, hour=16, minute=38, args=[bot])
    scheduler.start()
    logger.info(
        "Bot started",
        extra={
            "send_to_telegram": True,
            "telegram_message": "🤖 Бот запущен\nстатус: ok",
        },
    )
    logger.info("Scheduler started with jobs: %s", scheduler.get_jobs())

    try:
        await dp.start_polling(bot)
    finally:
        logger.info(
            "Bot shutdown",
            extra={
                "send_to_telegram": True,
                "telegram_message": "🛑 Бот остановлен\nстатус: ok",
            },
        )
        scheduler.shutdown(wait=False)
        await shutdown_telegram_logging()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown")
