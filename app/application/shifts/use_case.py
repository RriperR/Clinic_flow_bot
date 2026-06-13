from collections.abc import Callable
from datetime import datetime

from app.application.shifts.dto import (
    DoctorShiftSignup,
    ShiftSignupOffer,
    ShiftSignupSelection,
    ShiftSignupStatus,
)
from app.application.shifts.ports import ShiftUnitOfWork
from app.domain.entities import Worker
from app.domain.repositories import ShiftRepository, WorkerRepository
from app.domain.shift_values import format_shift_date, ShiftType
from app.domain.shifts.scheduling import ShiftSchedule, SignupRejection
from app.text_utils import normalize_text

_REJECTION_STATUS = {
    SignupRejection.SHIFT_NOT_FOUND: ShiftSignupStatus.SHIFT_NOT_FOUND,
    SignupRejection.SHIFT_UNAVAILABLE: ShiftSignupStatus.SHIFT_UNAVAILABLE,
    SignupRejection.SHIFT_TAKEN: ShiftSignupStatus.SHIFT_TAKEN,
    SignupRejection.ASSISTANT_ALREADY_ASSIGNED: ShiftSignupStatus.ALREADY_HAS_SHIFT,
}


def detect_shift_type(hour: int, minute: int = 0) -> ShiftType | None:
    current_minutes = hour * 60 + minute
    if 7 * 60 + 30 <= current_minutes < 14 * 60:
        return ShiftType.MORNING
    if 14 * 60 <= current_minutes < 21 * 60:
        return ShiftType.EVENING
    return None


class ShiftService:
    def __init__(
        self,
        workers: WorkerRepository,
        shifts: ShiftRepository,
        uow_factory: Callable[[], ShiftUnitOfWork],
    ):
        self.workers = workers
        # self.shifts используется для чистых чтений; запись идёт через UoW,
        # чтобы загрузка слота и изменение смены жили в одной транзакции.
        self.shifts = shifts
        self._uow_factory = uow_factory

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

    async def _load_schedule(self, date: str, shift_type: str) -> ShiftSchedule:
        shifts = await self.shifts.list_by_date(date)
        return ShiftSchedule(date, shift_type, shifts)

    async def prepare_signup(self, worker: Worker, date: str, shift_type: str) -> ShiftSignupOffer:
        schedule = await self._load_schedule(date, shift_type)
        current_shift = schedule.assistant_shift(worker.id)
        if current_shift:
            return ShiftSignupOffer(
                status=ShiftSignupStatus.CURRENT_SHIFT_EXISTS,
                current_shift=current_shift,
                free_shifts=[],
            )
        free_shifts = await self.list_free_shifts(date, shift_type, worker.full_name)
        status = ShiftSignupStatus.READY if free_shifts else ShiftSignupStatus.NO_FREE_SHIFTS
        return ShiftSignupOffer(status=status, current_shift=None, free_shifts=free_shifts)

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
                label = f"в­ђ {label}"
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
        # Чтение слота, доменная проверка и запись — в одной транзакции UoW.
        async with self._uow_factory() as uow:
            schedule = ShiftSchedule(date, shift_type, await uow.shifts.list_by_date(date))
            shift = await uow.shifts.get_by_id(shift_id)
            rejection = schedule.evaluate_signup(shift, worker.id)
            if rejection:
                rejected_shift = (
                    schedule.assistant_shift(worker.id)
                    if rejection == SignupRejection.ASSISTANT_ALREADY_ASSIGNED
                    else shift
                )
                return ShiftSignupSelection(status=_REJECTION_STATUS[rejection], shift=rejected_shift)

            success = await uow.shifts.add_by_id(worker.id, worker.full_name, shift_id)
            if success:
                await uow.commit()
            status = ShiftSignupStatus.SIGNED_UP if success else ShiftSignupStatus.SHIFT_TAKEN
            return ShiftSignupSelection(status=status, shift=shift)

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
            return DoctorShiftSignup(status=ShiftSignupStatus.DOCTOR_NOT_FOUND, doctor=None)

        doctor_shifts = await self.list_doctor_shifts(date, shift_type, doctor.full_name)
        if not doctor_shifts:
            return DoctorShiftSignup(
                status=ShiftSignupStatus.NEEDS_MANUAL_CONFIRMATION,
                doctor=doctor,
            )

        free_slot = await self.get_preferred_free_doctor_slot(
            date,
            shift_type,
            doctor.full_name,
            worker.full_name,
        )
        if not free_slot or free_slot.id is None:
            return DoctorShiftSignup(
                status=ShiftSignupStatus.NEEDS_MANUAL_CONFIRMATION,
                doctor=doctor,
                has_schedule_slots=True,
            )

        selection = await self.signup_by_shift_id(worker, date, shift_type, free_slot.id)
        return DoctorShiftSignup(
            status=selection.status,
            doctor=doctor,
            has_schedule_slots=True,
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
            return DoctorShiftSignup(status=ShiftSignupStatus.DOCTOR_NOT_FOUND, doctor=None)

        free_slot = await self.get_preferred_free_doctor_slot(
            date,
            shift_type,
            doctor.full_name,
            worker.full_name,
        )
        if free_slot and free_slot.id is not None:
            selection = await self.signup_by_shift_id(worker, date, shift_type, free_slot.id)
            status = selection.status
        else:
            async with self._uow_factory() as uow:
                schedule = ShiftSchedule(date, shift_type, await uow.shifts.list_by_date(date))
                if schedule.has_assistant(worker.id):
                    status = ShiftSignupStatus.ALREADY_HAS_SHIFT
                else:
                    success = await uow.shifts.add_manual(
                        worker.id,
                        worker.full_name,
                        doctor.full_name,
                        shift_type,
                        date,
                    )
                    if success:
                        await uow.commit()
                    status = ShiftSignupStatus.SIGNED_UP if success else ShiftSignupStatus.ALREADY_HAS_SHIFT

        return DoctorShiftSignup(
            status=status,
            doctor=doctor,
            has_schedule_slots=free_slot is not None,
        )

    async def get_shift_by_id(self, shift_id: int):
        return await self.shifts.get_by_id(shift_id)

    def guess_shift_type_from_now(self) -> tuple[ShiftType | None, str]:
        now = datetime.now()
        shift_type = detect_shift_type(now.hour, now.minute)
        date_str = format_shift_date(now)
        return shift_type, date_str
