from app.domain.entities import Worker
from app.domain.repositories import WorkerRepository


class WorkerReportService:
    def __init__(self, workers: WorkerRepository):
        self.workers = workers

    async def build_report_for_chat_id(self, chat_id: int) -> str | None:
        worker = await self.workers.get_by_chat_id(chat_id)
        if not worker:
            return None
        return self.build_report_for_worker(worker)

    @staticmethod
    def build_report_for_worker(worker: Worker) -> str:
        return (
            "Отчёт без учёта сегодняшних смен:\n"
            "За неделю:\n"
            f"смен: {worker.shifts_week}\n"
            f"отдано: {worker.given_week}\n"
            f"выходов на замену: {worker.replacement_week}\n"
            f"смен выбрано вручную: {worker.manual_week}\n\n"
            "За месяц:\n"
            f"всего смен: {worker.shifts_month}\n"
            f"отдано смен: {worker.given_month}\n"
            f"выходов на замену: {worker.replacement_month}\n"
            f"смен выбрано вручную: {worker.manual_month}"
        )
