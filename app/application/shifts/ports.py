from __future__ import annotations

from typing import Protocol

from app.domain.shifts.repositories import ShiftRepository


class ShiftUnitOfWork(Protocol):
    """Транзакционная граница для записи смен.

    Репозитории внутри одного UoW работают на общей сессии; изменения
    фиксируются единственным commit(), иначе откатываются при выходе.
    """

    shifts: ShiftRepository

    async def __aenter__(self) -> ShiftUnitOfWork: ...
    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
