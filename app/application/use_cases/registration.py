from app.domain.entities import Worker
from app.domain.repositories import WorkerRepository
from app.infrastructure.sheets.gateway import SheetsGateway
from app.logger import setup_logger


logger = setup_logger("registration", "reg.log")


class RegistrationService:
    def __init__(self, workers: WorkerRepository, sheets: SheetsGateway | None = None):
        self.workers = workers
        self.sheets = sheets

    async def list_unregistered(self) -> list[Worker]:
        return list(await self.workers.list_unregistered())

    async def set_chat_id(self, worker_id: int, chat_id: str) -> bool:
        success = await self.workers.set_chat_id(worker_id, chat_id)
        if success and self.sheets:
            try:
                worker = await self.workers.get_by_id(worker_id)
                if worker:
                    self.sheets.upsert_worker_registration(
                        worker.full_name, chat_id=chat_id
                    )
            except Exception:
                logger.exception("Failed to sync worker chat_id to Google Sheets")
        return success

    async def set_worker_photo(self, worker_id: int, file_id: str) -> None:
        await self.workers.set_file_id(worker_id, file_id)
        if self.sheets:
            try:
                worker = await self.workers.get_by_id(worker_id)
                if worker:
                    self.sheets.upsert_worker_registration(
                        worker.full_name, file_id=file_id
                    )
            except Exception:
                logger.exception("Failed to sync worker file_id to Google Sheets")

    async def get_by_chat_id(
        self, chat_id: int, include_inactive: bool = False
    ) -> Worker | None:
        return await self.workers.get_by_chat_id(
            chat_id, include_inactive=include_inactive
        )

    async def get_by_id(self, worker_id: int) -> Worker | None:
        return await self.workers.get_by_id(worker_id)
