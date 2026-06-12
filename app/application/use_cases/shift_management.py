from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import Shift, Worker
from app.domain.repositories import ShiftRepository, WorkerRepository
from app.text_utils import normalize_text


@dataclass
class ShiftSignupOffer:
    current_shift: Shift | None
    free_shifts: list[tuple[int, str]]


@dataclass
class ShiftSignupSelection:
    shift: Shift | None
    success: bool


@dataclass
class DoctorShiftSignup:
    doctor: Worker | None
    has_schedule_slots: bool = False
    requires_confirmation: bool = False
    success: bool = False


def detect_shift_type(hour: int, minute: int = 0) -> str | None:
    current_minutes = hour * 60 + minute
    if 7 * 60 + 30 <= current_minutes < 14 * 60:
        return "morning"
    if 14 * 60 <= current_minutes < 21 * 60:
        return "evening"
    return None


class ShiftService:
    def __init__(self, workers: WorkerRepository, shifts: ShiftRepository):
        self.workers = workers
        self.shifts = shifts

    async def get_worker(self, chat_id: int, include_inactive: bool = False):
        return await self.workers.get_by_chat_id(chat_id, include_inactive=include_inactive)

    async def get_worker_by_id(self, worker_id: int):
        return await self.workers.get_by_id(worker_id)

    async def list_all_doctors(self):
        return await self.workers.list_all()

    async def list_doctor_shifts(self, date: str, shift_type: str, doctor_name: str):
        normalized = normalize_text(doctor_name)
        shifts = [
            shift
            for shift in await self.shifts.list_by_date(date)
            if shift.type == shift_type and normalize_text(shift.doctor_name) == normalized
        ]
        shifts.sort(key=lambda item: item.id or 0)
        return shifts

    async def get_preferred_free_doctor_slot(
        self,
        date: str,
        shift_type: str,
        doctor_name: str,
        assistant_name: str | None = None,
    ):
        doctor_shifts = await self.list_doctor_shifts(date, shift_type, doctor_name)
        free_slots = [shift for shift in doctor_shifts if shift.assistant_id is None]
        if not free_slots:
            return None

        preferred = normalize_text(assistant_name)
        if preferred:
            scheduled_slots = [
                shift for shift in free_slots if normalize_text(shift.scheduled_assistant_name) == preferred
            ]
            if scheduled_slots:
                scheduled_slots.sort(key=lambda item: item.id or 0)
                return scheduled_slots[0]

        free_slots.sort(key=lambda item: item.id or 0)
        return free_slots[0]

    async def get_current_shift(self, worker_id: int, date: str, shift_type: str):
        return await self.shifts.get_for_assistant(worker_id, date, shift_type)

    async def prepare_signup(self, worker: Worker, date: str, shift_type: str) -> ShiftSignupOffer:
        current_shift = await self.get_current_shift(worker.id, date, shift_type)
        if current_shift:
            return ShiftSignupOffer(current_shift=current_shift, free_shifts=[])
        free_shifts = await self.list_free_shifts(date, shift_type, worker.full_name)
        return ShiftSignupOffer(current_shift=None, free_shifts=free_shifts)

    async def list_free_shifts(self, date: str, shift_type: str, assistant_name: str | None = None):
        shifts = [
            shift
            for shift in await self.shifts.list_by_date(date)
            if shift.type == shift_type and shift.assistant_id is None
        ]
        preferred = normalize_text(assistant_name)

        def is_preferred(item) -> bool:
            return item.scheduled_assistant_name and normalize_text(item.scheduled_assistant_name) == preferred

        shifts.sort(
            key=lambda item: (
                0 if preferred and is_preferred(item) else 1,
                normalize_text(item.doctor_name),
                item.id or 0,
            )
        )

        result: list[tuple[int, str]] = []
        for shift in shifts:
            if shift.id is None:
                continue
            label = shift.doctor_name
            if preferred and is_preferred(shift):
                label = f"⭐ {label}"
            result.append((shift.id, label))
        return result

    async def add_shift_by_id(self, worker_id: int, worker_name: str, shift_id: int) -> bool:
        return await self.shifts.add_by_id(worker_id, worker_name, shift_id)

    async def signup_by_shift_id(
        self,
        worker: Worker,
        date: str,
        shift_type: str,
        shift_id: int,
    ) -> ShiftSignupSelection:
        shift = await self.get_shift_by_id(shift_id)
        if not shift or shift.date != date or shift.type != shift_type:
            return ShiftSignupSelection(shift=shift, success=False)
        success = await self.add_shift_by_id(worker.id, worker.full_name, shift_id)
        return ShiftSignupSelection(shift=shift, success=success)

    async def remove_shift(self, assistant_id: int, date: str, shift_type: str) -> None:
        await self.shifts.remove_assistant(assistant_id, date, shift_type)

    async def add_manual_shift(
        self,
        assistant_id: int,
        assistant_name: str,
        doctor_name: str,
        shift_type: str,
        date: str,
    ) -> bool:
        return await self.shifts.add_manual(assistant_id, assistant_name, doctor_name, shift_type, date)

    async def signup_to_doctor(
        self,
        worker: Worker,
        doctor_id: int,
        date: str,
        shift_type: str,
    ) -> DoctorShiftSignup:
        doctor = await self.get_worker_by_id(doctor_id)
        if not doctor:
            return DoctorShiftSignup(doctor=None)

        doctor_shifts = await self.list_doctor_shifts(date, shift_type, doctor.full_name)
        if not doctor_shifts:
            return DoctorShiftSignup(doctor=doctor, requires_confirmation=True)

        free_slot = await self.get_preferred_free_doctor_slot(
            date,
            shift_type,
            doctor.full_name,
            worker.full_name,
        )
        if not free_slot or free_slot.id is None:
            return DoctorShiftSignup(
                doctor=doctor,
                has_schedule_slots=True,
                requires_confirmation=True,
            )

        success = await self.add_shift_by_id(worker.id, worker.full_name, free_slot.id)
        return DoctorShiftSignup(
            doctor=doctor,
            has_schedule_slots=True,
            success=success,
        )

    async def confirm_manual_signup(
        self,
        worker: Worker,
        doctor_id: int,
        date: str,
        shift_type: str,
    ) -> DoctorShiftSignup:
        doctor = await self.get_worker_by_id(doctor_id)
        if not doctor:
            return DoctorShiftSignup(doctor=None)

        free_slot = await self.get_preferred_free_doctor_slot(
            date,
            shift_type,
            doctor.full_name,
            worker.full_name,
        )
        if free_slot and free_slot.id is not None:
            success = await self.add_shift_by_id(worker.id, worker.full_name, free_slot.id)
        else:
            success = await self.add_manual_shift(
                worker.id,
                worker.full_name,
                doctor.full_name,
                shift_type,
                date,
            )

        return DoctorShiftSignup(
            doctor=doctor,
            has_schedule_slots=free_slot is not None,
            success=success,
        )

    async def get_shift_by_id(self, shift_id: int):
        return await self.shifts.get_by_id(shift_id)

    def guess_shift_type_from_now(self) -> tuple[str | None, str]:
        now = datetime.now()
        shift_type = detect_shift_type(now.hour, now.minute)
        date_str = now.strftime("%d.%m.%Y")
        return shift_type, date_str
