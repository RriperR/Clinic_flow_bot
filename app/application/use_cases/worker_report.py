from app.domain.entities import Worker
from app.domain.repositories import WorkerRepository
from app.infrastructure.sheets.gateway import SheetsGateway
from app.text_utils import normalize_text


class WorkerReportService:
    def __init__(self, workers: WorkerRepository, gateway: SheetsGateway):
        self.workers = workers
        self.gateway = gateway

    async def build_report_for_chat_id(self, chat_id: int) -> str | None:
        worker = await self.workers.get_by_chat_id(chat_id)
        if not worker:
            return None
        return self.build_report_for_worker(worker)

    def build_report_for_worker(self, worker: Worker) -> str | None:
        rows = self.gateway.read_workers()
        row = self._find_row(rows, worker)
        if not row:
            return None

        shifts_week = self._cell(row, 5)
        shifts_month = self._cell(row, 6)
        given_week = self._cell(row, 7)
        given_month = self._cell(row, 8)
        replacement_week = self._cell(row, 9)
        replacement_month = self._cell(row, 10)
        manual_week = self._cell(row, 11)
        manual_month = self._cell(row, 12)

        return (
            "Отчёт по сменам:\n"
            f"Всего смен — неделя: {shifts_week}, месяц: {shifts_month}\n"
            f"Отдано смен — неделя: {given_week}, месяц: {given_month}\n"
            f"Выход на замену — неделя: {replacement_week}, месяц: {replacement_month}\n"
            f"Ручной выбор — неделя: {manual_week}, месяц: {manual_month}"
        )

    def _find_row(self, rows: list[list[str]], worker: Worker) -> list[str] | None:
        chat_id = (worker.chat_id or "").strip()
        worker_name = normalize_text(worker.full_name)

        if chat_id:
            for row in rows:
                row_chat_id = row[2].strip() if len(row) > 2 else ""
                if row_chat_id and row_chat_id == chat_id:
                    return row

        for row in rows:
            full_name = row[0] if row else ""
            if normalize_text(full_name) == worker_name:
                return row

        return None

    @staticmethod
    def _cell(row: list[str], index: int) -> str:
        if index >= len(row):
            return "0"
        value = row[index].strip()
        return value if value else "0"
