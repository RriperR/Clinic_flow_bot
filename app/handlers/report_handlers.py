from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.application.reports.worker_report_use_case import WorkerReportService
from app.logger import setup_logger
from app.presentation.reports.formatters import format_worker_shift_report

logger = setup_logger("report", "report.log")


def create_report_router(report_service: WorkerReportService) -> Router:
    router = Router()

    @router.message(Command("report"))
    async def report(message: Message):
        try:
            report = await report_service.get_report_for_chat_id(message.from_user.id)
        except Exception:
            logger.exception("Failed to build worker report for chat_id=%s", message.from_user.id)
            await message.answer("Не удалось получить отчёт. Попробуйте позже.")
            return

        if not report:
            await message.answer("Мы не нашли вас в списке сотрудников.")
            return

        await message.answer(format_worker_shift_report(report))

    return router
