from datetime import datetime

from app.domain.entities import AdminUser, Worker
from app.domain.repositories import AdminRepository, WorkerRepository


class AdminAccessService:
    def __init__(
        self,
        admins: AdminRepository,
        workers: WorkerRepository,
        super_admin_ids: set[str],
    ):
        self.admins = admins
        self.workers = workers
        self.super_admin_ids = {str(item).strip() for item in super_admin_ids if str(item).strip()}

    def is_super_admin(self, chat_id: int | str) -> bool:
        return str(chat_id) in self.super_admin_ids

    def list_super_admins(self) -> list[str]:
        return sorted(self.super_admin_ids)

    async def is_admin(self, chat_id: int | str) -> bool:
        if self.is_super_admin(chat_id):
            return True
        return await self.admins.exists(str(chat_id))

    async def list_admins(self) -> list[AdminUser]:
        return list(await self.admins.list_all())

    async def list_registered_workers(self) -> list[Worker]:
        workers = list(await self.workers.list_all())
        return [worker for worker in workers if worker.chat_id and worker.chat_id.strip()]

    async def add_admin(self, chat_id: str) -> bool:
        admin = AdminUser(
            chat_id=chat_id,
            added_at=datetime.now(),
        )
        return await self.admins.add(admin)

    async def remove_admin(self, chat_id: str) -> bool:
        return await self.admins.delete_by_chat_id(chat_id)

    async def resolve_worker_name(self, chat_id: str) -> str | None:
        try:
            worker = await self.workers.get_by_chat_id(int(chat_id))
        except ValueError:
            return None
        if not worker:
            return None
        return worker.full_name
