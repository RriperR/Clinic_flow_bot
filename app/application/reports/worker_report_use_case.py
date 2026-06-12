from app.application.reports.dto import WorkerShiftReport
from app.domain.entities import Worker
from app.domain.repositories import WorkerRepository


class WorkerReportService:
    def __init__(self, workers: WorkerRepository):
        self.workers = workers

    async def get_report_for_chat_id(self, chat_id: int) -> WorkerShiftReport | None:
        worker = await self.workers.get_by_chat_id(chat_id)
        if not worker:
            return None
        return self.build_report_for_worker(worker)

    @staticmethod
    def build_report_for_worker(worker: Worker) -> WorkerShiftReport:
        return WorkerShiftReport(
            shifts_week=worker.shifts_week,
            shifts_month=worker.shifts_month,
            given_week=worker.given_week,
            given_month=worker.given_month,
            replacement_week=worker.replacement_week,
            replacement_month=worker.replacement_month,
            manual_week=worker.manual_week,
            manual_month=worker.manual_month,
        )
