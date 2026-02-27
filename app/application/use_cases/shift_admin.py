from datetime import datetime

from app.domain.repositories import WorkerRepository, ShiftRepository
from app.text_utils import normalize_text


class ShiftAdminService:
    def __init__(self, workers: WorkerRepository, shifts: ShiftRepository):
        self.workers = workers
        self.shifts = shifts

    @staticmethod
    def _today_str() -> str:
        return datetime.now().strftime("%d.%m.%Y")

    async def list_today_shifts(self):
        date_str = self._today_str()
        shifts = list(await self.shifts.list_by_date(date_str))
        order = {"morning": 0, "evening": 1}
        shifts.sort(
            key=lambda s: (
                order.get(s.type, 2),
                normalize_text(s.doctor_name),
                s.id or 0,
            )
        )
        return shifts

    async def list_workers(self):
        return list(await self.workers.list_all())

    async def get_worker(self, worker_id: int):
        return await self.workers.get_by_id(worker_id)

    async def get_shift(self, shift_id: int):
        return await self.shifts.get_by_id(shift_id)

    async def create_shift_today(self, doctor_name: str, shift_type: str) -> bool:
        date_str = self._today_str()
        existing = [
            s
            for s in await self.list_today_shifts()
            if s.doctor_name == doctor_name and s.type == shift_type
        ]
        if existing:
            return False
        return await self.shifts.add_slot(doctor_name, date_str, shift_type)

    async def delete_shift_today(self, shift_id: int) -> bool:
        shift = await self.shifts.get_by_id(shift_id)
        if not shift:
            return False
        if shift.date != self._today_str():
            return False
        return await self.shifts.delete_by_id(shift_id)
