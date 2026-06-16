from datetime import date

from app.application.agent.shift_tools import build_shift_tools
from app.application.agent.tools import AgentToolContext, ToolRegistry
from app.application.shifts.use_case import ShiftService
from app.domain.entities import Shift, Worker


class FakeWorkerRepository:
    def __init__(self, workers: list[Worker]):
        self.workers = {worker.id: worker for worker in workers}

    async def get_by_id(self, worker_id: int, include_inactive: bool = False):
        return self.workers.get(worker_id)

    async def get_by_chat_id(self, chat_id: int, include_inactive: bool = False):
        for worker in self.workers.values():
            if worker.chat_id == str(chat_id):
                return worker
        return None

    async def list_all(self, include_inactive: bool = False):
        return list(self.workers.values())


class FakeShiftRepository:
    def __init__(self, shifts: list[Shift]):
        self.shifts = {shift.id: shift for shift in shifts}

    async def list_by_date(self, shift_date: date):
        return [shift for shift in self.shifts.values() if shift.date == shift_date]

    async def get_by_id(self, shift_id: int):
        return self.shifts.get(shift_id)

    async def get_for_assistant(self, assistant_id: int, shift_date: date, shift_type: str):
        for shift in self.shifts.values():
            if shift.assistant_id == assistant_id and shift.date == shift_date and shift.type == shift_type:
                return shift
        return None

    async def add_by_id(self, assistant_id: int, assistant_name: str, shift_id: int) -> bool:
        shift = self.shifts.get(shift_id)
        if not shift or shift.assistant_id is not None:
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
        shift_date: date,
    ) -> bool:
        self.shifts[max(self.shifts) + 1] = Shift(
            id=max(self.shifts) + 1,
            assistant_id=assistant_id,
            assistant_name=assistant_name,
            doctor_name=doctor_name,
            date=shift_date,
            type=shift_type,
            manual=True,
        )
        return True


class FakeUnitOfWork:
    def __init__(self, shifts: FakeShiftRepository):
        self.shifts = shifts

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def commit(self):
        pass


def build_service(shifts: list[Shift]) -> ShiftService:
    worker = Worker(id=1, full_name="Ассистент", chat_id="100")
    target = Worker(id=2, full_name="Иванова Мария Сергеевна")
    shift_repo = FakeShiftRepository(shifts)
    service = ShiftService(FakeWorkerRepository([worker, target]), shift_repo, lambda: FakeUnitOfWork(shift_repo))
    service.guess_shift_type_from_now = lambda: ("morning", date(2026, 1, 2))
    return service


async def test_prepare_shift_signup_does_not_write_before_confirmation() -> None:
    shift = Shift(
        id=10,
        assistant_id=None,
        doctor_name="Иванова Мария Сергеевна",
        date=date(2026, 1, 2),
        type="morning",
    )
    registry = ToolRegistry(build_shift_tools(build_service([shift])))
    context = AgentToolContext(
        chat_id=100,
        targets={"[SHIFT_TARGET_1]": 2},
        labels={"[SHIFT_TARGET_1]": "Иванова Мария Сергеевна"},
    )

    result = await registry.invoke("prepare_shift_signup", {"target_ref": "[SHIFT_TARGET_1]"}, context)

    assert '"status": "ready_for_confirmation"' in result.content
    assert result.pending_action is not None
    assert result.pending_action.kind == "shift_signup"
    assert not result.pending_action.manual
    assert shift.assistant_id is None


async def test_prepare_shift_signup_marks_manual_when_target_has_no_schedule() -> None:
    registry = ToolRegistry(build_shift_tools(build_service([])))
    context = AgentToolContext(
        chat_id=100,
        targets={"[SHIFT_TARGET_1]": 2},
        labels={"[SHIFT_TARGET_1]": "Иванова Мария Сергеевна"},
    )

    result = await registry.invoke("prepare_shift_signup", {"target_ref": "[SHIFT_TARGET_1]"}, context)

    assert "needs_manual_confirmation_no_schedule" in result.content
    assert result.pending_action is not None
    assert result.pending_action.manual


async def test_check_shift_availability_is_read_only() -> None:
    shift = Shift(
        id=10,
        assistant_id=5,
        doctor_name="Иванова Мария Сергеевна",
        date=date(2026, 1, 2),
        type="morning",
    )
    registry = ToolRegistry(build_shift_tools(build_service([shift])))
    context = AgentToolContext(chat_id=100, targets={"[SHIFT_TARGET_1]": 2}, labels={})

    result = await registry.invoke("check_shift_availability", {"target_ref": "[SHIFT_TARGET_1]"}, context)

    assert "all_slots_taken" in result.content
    assert result.pending_action is None
    assert shift.assistant_id == 5
