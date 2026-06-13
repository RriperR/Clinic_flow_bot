from __future__ import annotations

from app.infrastructure.db.models import async_session
from app.infrastructure.db.repositories import SqlAlchemyShiftRepository


class SqlAlchemyUnitOfWork:
    """Unit of Work на SQLAlchemy-сессии.

    Репозитории создаются на одной сессии, поэтому чтение и запись внутри
    одного блока `async with` видят согласованное состояние и фиксируются
    одним commit(). При выходе с исключением транзакция откатывается.
    """

    shifts: SqlAlchemyShiftRepository

    def __init__(self, session_factory=async_session):
        self._session_factory = session_factory

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.shifts = SqlAlchemyShiftRepository(self._session)
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        try:
            if exc_type is not None:
                await self._session.rollback()
        finally:
            await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
