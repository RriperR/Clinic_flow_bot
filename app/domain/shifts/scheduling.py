from collections.abc import Sequence
from enum import StrEnum

from app.domain.shifts.entities import Shift
from app.domain.shifts.value_objects import parse_shift_type, ShiftType


class SignupRejection(StrEnum):
    """Причина, по которой ассистента нельзя записать на смену в слоте."""

    SHIFT_NOT_FOUND = "shift_not_found"
    SHIFT_UNAVAILABLE = "shift_unavailable"
    SHIFT_TAKEN = "shift_taken"
    ASSISTANT_ALREADY_ASSIGNED = "assistant_already_assigned"


class ShiftSchedule:
    """Смены одного слота — конкретной даты и типа (утро/вечер).

    Инвариант слота: один ассистент занимает не больше одной смены.
    Правило проверяется по уже загруженному состоянию слота, без обращения к БД,
    поэтому его можно проверить и протестировать в отрыве от хранилища.
    """

    def __init__(self, date: str, shift_type: ShiftType | str, shifts: Sequence[Shift]):
        self.date = date
        self.shift_type = parse_shift_type(shift_type)
        self._shifts = [shift for shift in shifts if self._belongs(shift)]

    def _belongs(self, shift: Shift) -> bool:
        return shift.date == self.date and parse_shift_type(shift.type) == self.shift_type

    def assistant_shift(self, assistant_id: int) -> Shift | None:
        """Смена слота, на которой уже стоит ассистент, либо None."""
        return next((shift for shift in self._shifts if shift.assistant_id == assistant_id), None)

    def has_assistant(self, assistant_id: int) -> bool:
        return self.assistant_shift(assistant_id) is not None

    def evaluate_signup(self, shift: Shift | None, assistant_id: int) -> SignupRejection | None:
        """Проверить, можно ли записать ассистента на shift.

        Возвращает причину отказа либо None, если запись разрешена.
        """
        if shift is None:
            return SignupRejection.SHIFT_NOT_FOUND
        if not self._belongs(shift):
            return SignupRejection.SHIFT_UNAVAILABLE
        if shift.assistant_id is not None:
            return SignupRejection.SHIFT_TAKEN
        if self.has_assistant(assistant_id):
            return SignupRejection.ASSISTANT_ALREADY_ASSIGNED
        return None
