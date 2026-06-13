from datetime import date

from app.domain.entities import Shift
from app.domain.shifts.scheduling import ShiftSchedule, SignupRejection

DATE = date(2026, 1, 2)


def _free_shift(shift_id: int, doctor: str = "Doctor") -> Shift:
    return Shift(id=shift_id, assistant_id=None, doctor_name=doctor, date=DATE, type="morning")


def _taken_shift(shift_id: int, assistant_id: int, doctor: str = "Doctor") -> Shift:
    return Shift(id=shift_id, assistant_id=assistant_id, doctor_name=doctor, date=DATE, type="morning")


def test_schedule_keeps_only_shifts_of_the_slot() -> None:
    other_day = Shift(id=2, assistant_id=None, doctor_name="Doctor", date=date(2026, 1, 3), type="morning")
    other_type = Shift(id=3, assistant_id=None, doctor_name="Doctor", date=DATE, type="evening")
    schedule = ShiftSchedule(DATE, "morning", [_free_shift(1), other_day, other_type])

    assert schedule.evaluate_signup(other_day, assistant_id=10) == SignupRejection.SHIFT_UNAVAILABLE
    assert schedule.evaluate_signup(other_type, assistant_id=10) == SignupRejection.SHIFT_UNAVAILABLE


def test_free_shift_can_be_taken() -> None:
    shift = _free_shift(1)
    schedule = ShiftSchedule(DATE, "morning", [shift])

    assert schedule.evaluate_signup(shift, assistant_id=10) is None


def test_missing_shift_is_rejected() -> None:
    schedule = ShiftSchedule(DATE, "morning", [])

    assert schedule.evaluate_signup(None, assistant_id=10) == SignupRejection.SHIFT_NOT_FOUND


def test_taken_shift_is_rejected() -> None:
    shift = _taken_shift(1, assistant_id=99)
    schedule = ShiftSchedule(DATE, "morning", [shift])

    assert schedule.evaluate_signup(shift, assistant_id=10) == SignupRejection.SHIFT_TAKEN


def test_assistant_with_existing_shift_cannot_take_another() -> None:
    own = _taken_shift(1, assistant_id=10, doctor="Doctor A")
    free = _free_shift(2, doctor="Doctor B")
    schedule = ShiftSchedule(DATE, "morning", [own, free])

    assert schedule.has_assistant(10)
    assert schedule.assistant_shift(10) is own
    assert schedule.evaluate_signup(free, assistant_id=10) == SignupRejection.ASSISTANT_ALREADY_ASSIGNED
