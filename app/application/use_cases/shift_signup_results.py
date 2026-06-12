from dataclasses import dataclass
from enum import StrEnum

from app.domain.entities import Shift, Worker


class ShiftSignupStatus(StrEnum):
    READY = "ready"
    CURRENT_SHIFT_EXISTS = "current_shift_exists"
    NO_FREE_SHIFTS = "no_free_shifts"
    SIGNED_UP = "signed_up"
    SHIFT_NOT_FOUND = "shift_not_found"
    SHIFT_UNAVAILABLE = "shift_unavailable"
    SHIFT_TAKEN = "shift_taken"
    ALREADY_HAS_SHIFT = "already_has_shift"
    DOCTOR_NOT_FOUND = "doctor_not_found"
    NEEDS_MANUAL_CONFIRMATION = "needs_manual_confirmation"


@dataclass
class ShiftSignupOffer:
    status: ShiftSignupStatus
    current_shift: Shift | None
    free_shifts: list[tuple[int, str]]


@dataclass
class ShiftSignupSelection:
    status: ShiftSignupStatus
    shift: Shift | None

    @property
    def success(self) -> bool:
        return self.status == ShiftSignupStatus.SIGNED_UP


@dataclass
class DoctorShiftSignup:
    status: ShiftSignupStatus
    doctor: Worker | None
    has_schedule_slots: bool = False

    @property
    def requires_confirmation(self) -> bool:
        return self.status == ShiftSignupStatus.NEEDS_MANUAL_CONFIRMATION

    @property
    def success(self) -> bool:
        return self.status == ShiftSignupStatus.SIGNED_UP
