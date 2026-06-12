from dataclasses import dataclass


@dataclass
class WorkerShiftReport:
    shifts_week: int
    shifts_month: int
    given_week: int
    given_month: int
    replacement_week: int
    replacement_month: int
    manual_week: int
    manual_month: int
