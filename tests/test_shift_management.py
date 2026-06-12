from datetime import date

from app.application.use_cases.shift_management import detect_shift_type, ShiftService
from app.application.use_cases.shift_signup_results import ShiftSignupStatus
from app.domain.entities import Shift, Worker
from app.domain.shift_values import format_shift_date, ShiftType


def test_detect_shift_type_allows_signup_until_21_00() -> None:
    assert detect_shift_type(7, 29) is None
    assert detect_shift_type(7, 30) == ShiftType.MORNING
    assert detect_shift_type(13, 59) == "morning"
    assert detect_shift_type(14, 0) == ShiftType.EVENING
    assert detect_shift_type(20, 59) == "evening"
    assert detect_shift_type(21, 0) is None


def test_format_shift_date_uses_domain_format() -> None:
    assert format_shift_date(date(2026, 1, 2)) == "02.01.2026"


class FakeWorkerRepository:
    def __init__(self, workers: list[Worker]):
        self.workers = {worker.id: worker for worker in workers}

    async def get_by_id(self, worker_id: int, include_inactive: bool = False):
        return self.workers.get(worker_id)

    async def get_by_chat_id(self, chat_id: int, include_inactive: bool = False):
        return None

    async def list_all(self, include_inactive: bool = False):
        return list(self.workers.values())


class FakeShiftRepository:
    def __init__(self, shifts: list[Shift]):
        self.shifts = {shift.id: shift for shift in shifts}

    async def list_by_date(self, date: str):
        return [shift for shift in self.shifts.values() if shift.date == date]

    async def get_by_id(self, shift_id: int):
        return self.shifts.get(shift_id)

    async def get_for_assistant(self, assistant_id: int, date: str, shift_type: str):
        for shift in self.shifts.values():
            if shift.assistant_id == assistant_id and shift.date == date and shift.type == shift_type:
                return shift
        return None

    async def add_by_id(self, assistant_id: int, assistant_name: str, shift_id: int) -> bool:
        shift = self.shifts.get(shift_id)
        if shift is None or shift.assistant_id is not None:
            return False
        shift.assistant_id = assistant_id
        shift.assistant_name = assistant_name
        return True

    async def add_manual(
        self,
        assistant_id: int,
        assistant_name: str,
        doctor_name: str,
        shift_type: str,
        date: str,
    ) -> bool:
        if await self.get_for_assistant(assistant_id, date, shift_type):
            return False
        self.shifts[max(self.shifts) + 1] = Shift(
            id=max(self.shifts) + 1,
            assistant_id=assistant_id,
            assistant_name=assistant_name,
            doctor_name=doctor_name,
            date=date,
            type=shift_type,
            manual=True,
        )
        return True


async def test_signup_by_shift_id_reports_unavailable_shift() -> None:
    worker = Worker(id=1, full_name="Assistant")
    service = ShiftService(
        FakeWorkerRepository([worker]),
        FakeShiftRepository([Shift(id=10, assistant_id=None, doctor_name="Doctor", date="02.01.2026", type="morning")]),
    )

    result = await service.signup_by_shift_id(worker, "01.01.2026", "morning", 10)

    assert result.status == ShiftSignupStatus.SHIFT_UNAVAILABLE
    assert not result.success


async def test_signup_to_doctor_reports_manual_confirmation_when_slots_are_taken() -> None:
    worker = Worker(id=1, full_name="Assistant")
    doctor = Worker(id=2, full_name="Doctor")
    service = ShiftService(
        FakeWorkerRepository([worker, doctor]),
        FakeShiftRepository([Shift(id=10, assistant_id=3, doctor_name="Doctor", date="01.01.2026", type="morning")]),
    )

    result = await service.signup_to_doctor(worker, doctor.id, "01.01.2026", "morning")

    assert result.status == ShiftSignupStatus.NEEDS_MANUAL_CONFIRMATION
    assert result.requires_confirmation
