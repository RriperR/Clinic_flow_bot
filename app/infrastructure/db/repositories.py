from contextlib import asynccontextmanager
from datetime import date as date_cls

from sqlalchemy import delete, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import (
    AdminUser as AdminUserEntity,
    Answer as AnswerEntity,
    Cabinet as CabinetEntity,
    Instrument as InstrumentEntity,
    InstrumentMove as InstrumentMoveEntity,
    KnowledgeItem as KnowledgeItemEntity,
    KnowledgeManipulation as KnowledgeManipulationEntity,
    KnowledgeSection as KnowledgeSectionEntity,
    Pair as PairEntity,
    Shift as ShiftEntity,
    Survey as SurveyEntity,
    Worker as WorkerEntity,
)
from app.domain.repositories import (
    AdminRepository,
    AnswerRepository,
    CabinetRepository,
    InstrumentMoveRepository,
    InstrumentRepository,
    KnowledgeBaseRepository,
    PairRepository,
    ShiftRepository,
    SurveyRepository,
    WorkerRepository,
)
from app.domain.shifts.value_objects import ShiftImportRow
from app.infrastructure.db.mappers import (
    from_admin_entity,
    from_answer_entity,
    from_cabinet_entity,
    from_instrument_entity,
    from_instrument_move_entity,
    from_knowledge_item_entity,
    from_knowledge_manipulation_entity,
    from_knowledge_section_entity,
    from_pair_entity,
    from_survey_entity,
    from_worker_entity,
    to_admin_entity,
    to_answer_entity,
    to_cabinet_entity,
    to_instrument_entity,
    to_instrument_move_entity,
    to_knowledge_item_entity,
    to_knowledge_manipulation_entity,
    to_knowledge_section_entity,
    to_pair_entity,
    to_shift_entity,
    to_survey_entity,
    to_worker_entity,
)
from app.infrastructure.db.models import (
    AdminUser as AdminUserModel,
    Answer as AnswerModel,
    async_session,
    Cabinet as CabinetModel,
    Instrument as InstrumentModel,
    InstrumentMove as InstrumentMoveModel,
    KnowledgeItem as KnowledgeItemModel,
    KnowledgeManipulation as KnowledgeManipulationModel,
    KnowledgeSection as KnowledgeSectionModel,
    Pair as PairModel,
    Shift as ShiftModel,
    Survey as SurveyModel,
    Worker as WorkerModel,
)


@asynccontextmanager
async def _session_scope(external: AsyncSession | None):
    """Дать сессию для работы репозитория.

    Если сессия пришла извне (из Unit of Work) — отдаём её и не управляем
    транзакцией: коммит/откат за вызывающим (owns=False). Иначе открываем
    собственную сессию и владеем её жизненным циклом (owns=True).
    """
    if external is not None:
        yield external, False
    else:
        async with async_session() as session:
            yield session, True


class SqlAlchemyAdminRepository(AdminRepository):
    async def list_all(self):
        async with async_session() as session:
            result = await session.execute(select(AdminUserModel).order_by(AdminUserModel.chat_id))
            return [to_admin_entity(item) for item in result.scalars().all()]

    async def get_by_chat_id(self, chat_id: str) -> AdminUserEntity | None:
        async with async_session() as session:
            stmt = select(AdminUserModel).where(AdminUserModel.chat_id == chat_id)
            result = await session.execute(stmt)
            return to_admin_entity(result.scalar_one_or_none())

    async def exists(self, chat_id: str) -> bool:
        async with async_session() as session:
            stmt = select(AdminUserModel.id).where(AdminUserModel.chat_id == chat_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def add(self, admin: AdminUserEntity) -> bool:
        async with async_session() as session:
            stmt = select(AdminUserModel.id).where(AdminUserModel.chat_id == admin.chat_id)
            existing = await session.execute(stmt)
            if existing.scalar_one_or_none():
                return False
            session.add(from_admin_entity(admin))
            await session.commit()
            return True

    async def delete_by_chat_id(self, chat_id: str) -> bool:
        async with async_session() as session:
            stmt = select(AdminUserModel).where(AdminUserModel.chat_id == chat_id)
            result = await session.execute(stmt)
            admin = result.scalar_one_or_none()
            if not admin:
                return False
            await session.delete(admin)
            await session.commit()
            return True


class SqlAlchemyWorkerRepository(WorkerRepository):
    @staticmethod
    def _active_clause():
        return or_(WorkerModel.is_active.is_(True), WorkerModel.is_active.is_(None))

    async def get_by_fullname(self, full_name: str, include_inactive: bool = False) -> WorkerEntity | None:
        async with async_session() as session:
            stmt = select(WorkerModel).where(WorkerModel.full_name == full_name)
            if not include_inactive:
                stmt = stmt.where(self._active_clause())
            result = await session.execute(stmt)
            return to_worker_entity(result.scalar_one_or_none())

    async def get_by_chat_id(self, chat_id: int, include_inactive: bool = False) -> WorkerEntity | None:
        async with async_session() as session:
            stmt = select(WorkerModel).where(WorkerModel.chat_id == str(chat_id))
            if not include_inactive:
                stmt = stmt.where(self._active_clause())
            stmt = stmt.order_by(
                WorkerModel.is_active.desc().nulls_last(),
                WorkerModel.id.desc(),
            ).limit(1)
            result = await session.execute(stmt)
            return to_worker_entity(result.scalar_one_or_none())

    async def get_by_id(self, worker_id: int, include_inactive: bool = False) -> WorkerEntity | None:
        async with async_session() as session:
            stmt = select(WorkerModel).where(WorkerModel.id == worker_id)
            if not include_inactive:
                stmt = stmt.where(self._active_clause())
            result = await session.execute(stmt)
            return to_worker_entity(result.scalar_one_or_none())

    async def list_all(self, include_inactive: bool = False):
        async with async_session() as session:
            stmt = select(WorkerModel)
            if not include_inactive:
                stmt = stmt.where(self._active_clause())
            result = await session.execute(stmt)
            return [to_worker_entity(item) for item in result.scalars().all()]

    async def list_unregistered(self):
        async with async_session() as session:
            stmt = select(WorkerModel).where(
                ((WorkerModel.chat_id.is_(None)) | (WorkerModel.chat_id == "")),
                self._active_clause(),
            )
            result = await session.execute(stmt)
            return [to_worker_entity(item) for item in result.scalars().all()]

    async def add(self, worker: WorkerEntity) -> None:
        async with async_session() as session:
            session.add(from_worker_entity(worker))
            await session.commit()

    async def set_chat_id(self, worker_id: int, chat_id: str) -> bool:
        async with async_session() as session:
            existing_stmt = select(WorkerModel).where(WorkerModel.chat_id == chat_id)
            result = await session.execute(existing_stmt)
            if result.scalar_one_or_none():
                return False

            stmt = update(WorkerModel).where(WorkerModel.id == worker_id).values(chat_id=chat_id)
            await session.execute(stmt)
            await session.commit()
            return True

    async def clear_chat_id(self, worker_id: int) -> bool:
        async with async_session() as session:
            worker = await session.get(WorkerModel, worker_id)
            if not worker:
                return False
            worker.chat_id = None
            await session.commit()
            return True

    async def set_file_id(self, worker_id: int, file_id: str) -> None:
        async with async_session() as session:
            worker = await session.get(WorkerModel, worker_id)
            if worker:
                worker.file_id = file_id
                await session.commit()

    async def set_active(self, worker_id: int, is_active: bool) -> bool:
        async with async_session() as session:
            worker = await session.get(WorkerModel, worker_id)
            if not worker:
                return False
            worker.is_active = is_active
            await session.commit()
            return True

    async def update_from_sync(
        self,
        worker_id: int,
        *,
        file_id: str | None,
        chat_id: str | None,
        speciality: str | None,
        phone: str | None,
        shifts_week: int,
        shifts_month: int,
        given_week: int,
        given_month: int,
        replacement_week: int,
        replacement_month: int,
        manual_week: int,
        manual_month: int,
        is_active: bool = True,
    ) -> bool:
        async with async_session() as session:
            stmt = (
                update(WorkerModel)
                .where(WorkerModel.id == worker_id)
                .values(
                    file_id=file_id or None,
                    chat_id=chat_id or None,
                    speciality=speciality or None,
                    phone=phone or None,
                    shifts_week=shifts_week,
                    shifts_month=shifts_month,
                    given_week=given_week,
                    given_month=given_month,
                    replacement_week=replacement_week,
                    replacement_month=replacement_month,
                    manual_week=manual_week,
                    manual_month=manual_month,
                    is_active=is_active,
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0


class SqlAlchemySurveyRepository(SurveyRepository):
    async def get_by_name(self, name: str) -> SurveyEntity | None:
        async with async_session() as session:
            stmt = select(SurveyModel).where(SurveyModel.speciality == name)
            result = await session.execute(stmt)
            return to_survey_entity(result.scalar_one_or_none())

    async def clear_all(self) -> None:
        async with async_session() as session:
            await session.execute(delete(SurveyModel))
            await session.commit()

    async def add(self, survey: SurveyEntity) -> None:
        async with async_session() as session:
            session.add(from_survey_entity(survey))
            if survey.id is not None:
                await session.flush()
                await session.execute(
                    text(
                        "SELECT setval("
                        "pg_get_serial_sequence('surveys', 'id'), "
                        "GREATEST((SELECT COALESCE(MAX(id), 1) FROM surveys), 1), "
                        "true"
                        ")"
                    )
                )
            await session.commit()


class SqlAlchemyPairRepository(PairRepository):
    async def list_ready_by_date(self, date: date_cls):
        async with async_session() as session:
            stmt = select(PairModel).where(PairModel.status == "ready", PairModel.date <= date).order_by(PairModel.id)
            result = await session.execute(stmt)
            return [to_pair_entity(item) for item in result.scalars().all()]

    async def next_ready_for_subject(self, subject: str) -> PairEntity | None:
        async with async_session() as session:
            stmt = (
                select(PairModel)
                .where(PairModel.subject == subject, PairModel.status == "ready")
                .order_by(PairModel.id)
                .limit(1)
            )
            result = await session.execute(stmt)
            return to_pair_entity(result.scalar_one_or_none())

    async def update_status(self, pair_id: int, status: str) -> None:
        async with async_session() as session:
            stmt = update(PairModel).where(PairModel.id == pair_id).values(status=status)
            await session.execute(stmt)
            await session.commit()

    async def reset_incomplete(self) -> None:
        async with async_session() as session:
            stmt = update(PairModel).where(PairModel.status == "in_progress").values(status="ready")
            await session.execute(stmt)
            await session.commit()

    async def add(self, pair: PairEntity) -> None:
        async with async_session() as session:
            session.add(from_pair_entity(pair))
            await session.commit()

    async def clear_all(self) -> None:
        async with async_session() as session:
            await session.execute(delete(PairModel))
            await session.commit()


class SqlAlchemyAnswerRepository(AnswerRepository):
    async def save(self, answer: AnswerEntity) -> None:
        async with async_session() as session:
            session.add(from_answer_entity(answer))
            await session.commit()

    async def list_all(self):
        async with async_session() as session:
            result = await session.execute(select(AnswerModel))
            return [to_answer_entity(item) for item in result.scalars().all()]


class SqlAlchemyShiftRepository(ShiftRepository):
    def __init__(self, session: AsyncSession | None = None):
        # session != None — репозиторий работает внутри Unit of Work на общей
        # сессии и не коммитит сам. session == None — открывает свою сессию
        # на каждый вызов (поведение по умолчанию для прямого использования).
        self._session = session

    async def clear_all(self) -> None:
        async with _session_scope(self._session) as (session, owns):
            await session.execute(delete(ShiftModel))
            if owns:
                await session.commit()

    async def bulk_insert(self, records: list[ShiftImportRow]) -> None:
        # Идемпотентность: повторный импорт того же расписания не плодит дубли.
        # Идентичность планового слота — кортеж его полей. Существующие ключи
        # грузим одним запросом по затронутым датам и сравниваем в Python, где
        # None == None (SQL `= NULL` для этого не годится), заодно отсекая
        # дубли внутри самого батча.
        if not records:
            return
        async with _session_scope(self._session) as (session, owns):
            dates = {row.date for row in records}
            existing_rows = await session.execute(
                select(
                    ShiftModel.doctor_name,
                    ShiftModel.date,
                    ShiftModel.type,
                    ShiftModel.scheduled_assistant_name,
                    ShiftModel.speciality,
                    ShiftModel.cabinet,
                ).where(ShiftModel.manual.is_(False), ShiftModel.date.in_(dates))
            )
            seen = {tuple(row) for row in existing_rows.all()}
            for row in records:
                key = (
                    row.doctor_name,
                    row.date,
                    str(row.type),
                    row.scheduled_assistant_name,
                    row.speciality,
                    row.cabinet,
                )
                if key in seen:
                    continue
                seen.add(key)
                session.add(
                    ShiftModel(
                        doctor_name=row.doctor_name,
                        date=row.date,
                        type=str(row.type),
                        scheduled_assistant_name=row.scheduled_assistant_name,
                        speciality=row.speciality,
                        cabinet=row.cabinet,
                        manual=False,
                    )
                )
            if owns:
                await session.commit()

    async def get_by_id(self, shift_id: int) -> ShiftEntity | None:
        async with _session_scope(self._session) as (session, _):
            shift = await session.get(ShiftModel, shift_id)
            return to_shift_entity(shift)

    async def get_for_assistant(self, assistant_id: int, date: date_cls, shift_type: str) -> ShiftEntity | None:
        async with _session_scope(self._session) as (session, _):
            result = await session.execute(
                select(ShiftModel).where(
                    ShiftModel.assistant_id == assistant_id,
                    ShiftModel.date == date,
                    ShiftModel.type == shift_type,
                )
            )
            return to_shift_entity(result.scalar_one_or_none())

    async def remove_assistant(self, assistant_id: int, date: date_cls, shift_type: str) -> None:
        async with _session_scope(self._session) as (session, owns):
            stmt = (
                update(ShiftModel)
                .where(
                    ShiftModel.assistant_id == assistant_id,
                    ShiftModel.date == date,
                    ShiftModel.type == shift_type,
                )
                .values(assistant_id=None, assistant_name=None)
            )
            await session.execute(stmt)
            if owns:
                await session.commit()

    async def add_by_id(self, assistant_id: int, assistant_name: str, shift_id: int) -> bool:
        # Бизнес-правило записи проверяет домен. Здесь — только атомарные
        # гарантии: условный UPDATE не даёт занять уже занятую смену, а
        # уникальный индекс (assistant_id, date, type) — записаться дважды
        # в один слот при гонке запросов.
        async with _session_scope(self._session) as (session, owns):
            stmt = (
                update(ShiftModel)
                .where(ShiftModel.id == shift_id, ShiftModel.assistant_id.is_(None))
                .values(assistant_id=assistant_id, assistant_name=assistant_name, manual=False)
            )
            try:
                result = await session.execute(stmt)
                if owns:
                    await session.commit()
                else:
                    await session.flush()
            except IntegrityError:
                await session.rollback()
                return False
            return result.rowcount > 0

    async def add_manual(
        self,
        assistant_id: int,
        assistant_name: str,
        doctor_name: str,
        shift_type: str,
        date: date_cls,
    ) -> bool:
        async with _session_scope(self._session) as (session, owns):
            shift = ShiftModel(
                assistant_id=assistant_id,
                assistant_name=assistant_name,
                doctor_name=doctor_name,
                type=shift_type,
                date=date,
                manual=True,
            )
            session.add(shift)
            try:
                if owns:
                    await session.commit()
                else:
                    await session.flush()
            except IntegrityError:
                await session.rollback()
                return False
            return True

    async def add_slot(self, doctor_name: str, date: date_cls, shift_type: str) -> bool:
        async with _session_scope(self._session) as (session, owns):
            existing = await session.execute(
                select(ShiftModel.id).where(
                    ShiftModel.doctor_name == doctor_name,
                    ShiftModel.date == date,
                    ShiftModel.type == shift_type,
                )
            )
            if existing.scalar_one_or_none():
                return False

            shift = ShiftModel(
                doctor_name=doctor_name,
                date=date,
                type=shift_type,
                manual=False,
            )
            session.add(shift)
            if owns:
                await session.commit()
            return True

    async def delete_by_id(self, shift_id: int) -> bool:
        async with _session_scope(self._session) as (session, owns):
            shift = await session.get(ShiftModel, shift_id)
            if not shift:
                return False
            await session.delete(shift)
            if owns:
                await session.commit()
            return True

    async def list_by_date(self, date: date_cls):
        async with _session_scope(self._session) as (session, _):
            result = await session.execute(select(ShiftModel).where(ShiftModel.date == date))
            return [to_shift_entity(item) for item in result.scalars().all()]

    async def list_all(self):
        async with _session_scope(self._session) as (session, _):
            result = await session.execute(select(ShiftModel))
            return [to_shift_entity(item) for item in result.scalars().all()]


class SqlAlchemyCabinetRepository(CabinetRepository):
    async def list_all(self, include_archived: bool = False):
        async with async_session() as session:
            stmt = select(CabinetModel).order_by(CabinetModel.name)
            if not include_archived:
                stmt = stmt.where(CabinetModel.is_active.is_(True))
            result = await session.execute(stmt)
            return [to_cabinet_entity(item) for item in result.scalars().all()]

    async def get_by_id(self, cabinet_id: int) -> CabinetEntity | None:
        async with async_session() as session:
            cabinet = await session.get(CabinetModel, cabinet_id)
            return to_cabinet_entity(cabinet)

    async def add(self, cabinet: CabinetEntity) -> None:
        async with async_session() as session:
            session.add(from_cabinet_entity(cabinet))
            await session.commit()

    async def update_name(self, cabinet_id: int, name: str) -> bool:
        async with async_session() as session:
            cabinet = await session.get(CabinetModel, cabinet_id)
            if not cabinet:
                return False
            cabinet.name = name
            await session.commit()
            return True

    async def set_active(self, cabinet_id: int, is_active: bool) -> bool:
        async with async_session() as session:
            cabinet = await session.get(CabinetModel, cabinet_id)
            if not cabinet:
                return False
            cabinet.is_active = is_active
            await session.commit()
            return True

    async def delete(self, cabinet_id: int) -> bool:
        async with async_session() as session:
            cabinet = await session.get(CabinetModel, cabinet_id)
            if not cabinet:
                return False
            await session.delete(cabinet)
            await session.commit()
            return True

    async def has_instruments(self, cabinet_id: int) -> bool:
        async with async_session() as session:
            result = await session.execute(
                select(InstrumentModel.id).where(InstrumentModel.cabinet_id == cabinet_id).limit(1)
            )
            return result.scalar_one_or_none() is not None


class SqlAlchemyInstrumentRepository(InstrumentRepository):
    async def list_by_cabinet(self, cabinet_id: int, include_archived: bool = False):
        async with async_session() as session:
            stmt = (
                select(InstrumentModel).where(InstrumentModel.cabinet_id == cabinet_id).order_by(InstrumentModel.name)
            )
            if not include_archived:
                stmt = stmt.where(InstrumentModel.is_active.is_(True))
            result = await session.execute(stmt)
            return [to_instrument_entity(item) for item in result.scalars().all()]

    async def get_by_id(self, instrument_id: int) -> InstrumentEntity | None:
        async with async_session() as session:
            instrument = await session.get(InstrumentModel, instrument_id)
            return to_instrument_entity(instrument)

    async def update_cabinet(self, instrument_id: int, cabinet_id: int) -> bool:
        async with async_session() as session:
            instrument = await session.get(InstrumentModel, instrument_id)
            if not instrument:
                return False
            instrument.cabinet_id = cabinet_id
            await session.commit()
            return True

    async def add(self, instrument: InstrumentEntity) -> None:
        async with async_session() as session:
            session.add(from_instrument_entity(instrument))
            await session.commit()

    async def update_name(self, instrument_id: int, name: str) -> bool:
        async with async_session() as session:
            instrument = await session.get(InstrumentModel, instrument_id)
            if not instrument:
                return False
            instrument.name = name
            await session.commit()
            return True

    async def set_active(self, instrument_id: int, is_active: bool) -> bool:
        async with async_session() as session:
            instrument = await session.get(InstrumentModel, instrument_id)
            if not instrument:
                return False
            instrument.is_active = is_active
            await session.commit()
            return True

    async def delete(self, instrument_id: int) -> bool:
        async with async_session() as session:
            instrument = await session.get(InstrumentModel, instrument_id)
            if not instrument:
                return False
            await session.delete(instrument)
            await session.commit()
            return True


class SqlAlchemyInstrumentMoveRepository(InstrumentMoveRepository):
    async def add(self, move: InstrumentMoveEntity) -> None:
        async with async_session() as session:
            session.add(from_instrument_move_entity(move))
            await session.commit()

    async def list_recent(self, limit: int = 20):
        async with async_session() as session:
            result = await session.execute(
                select(InstrumentMoveModel).order_by(InstrumentMoveModel.id.desc()).limit(limit)
            )
            return [to_instrument_move_entity(item) for item in result.scalars().all()]

    async def get_last_for_instrument(self, instrument_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(InstrumentMoveModel)
                .where(InstrumentMoveModel.instrument_id == instrument_id)
                .order_by(InstrumentMoveModel.id.desc())
                .limit(1)
            )
            return to_instrument_move_entity(result.scalar_one_or_none())

    async def get_by_id(self, move_id: int) -> InstrumentMoveEntity | None:
        async with async_session() as session:
            move = await session.get(InstrumentMoveModel, move_id)
            return to_instrument_move_entity(move)


class SqlAlchemyKnowledgeBaseRepository(KnowledgeBaseRepository):
    async def replace_all(
        self,
        sections: list[
            tuple[
                KnowledgeSectionEntity,
                list[tuple[KnowledgeManipulationEntity, list[KnowledgeItemEntity]]],
            ]
        ],
    ) -> None:
        async with async_session() as session, session.begin():
            await session.execute(delete(KnowledgeItemModel))
            await session.execute(delete(KnowledgeManipulationModel))
            await session.execute(delete(KnowledgeSectionModel))

            for section_entity, manipulations in sections:
                section = from_knowledge_section_entity(section_entity)
                session.add(section)
                await session.flush()

                for manipulation_entity, items in manipulations:
                    manipulation_entity.section_id = section.id
                    manipulation = from_knowledge_manipulation_entity(manipulation_entity)
                    session.add(manipulation)
                    await session.flush()

                    for item_entity in items:
                        item_entity.manipulation_id = manipulation.id
                        session.add(from_knowledge_item_entity(item_entity))

    async def list_sections(self):
        async with async_session() as session:
            result = await session.execute(
                select(KnowledgeSectionModel)
                .where(KnowledgeSectionModel.is_active.is_(True))
                .order_by(KnowledgeSectionModel.position, KnowledgeSectionModel.id)
            )
            return [to_knowledge_section_entity(item) for item in result.scalars().all()]

    async def get_section(self, section_id: int) -> KnowledgeSectionEntity | None:
        async with async_session() as session:
            section = await session.get(KnowledgeSectionModel, section_id)
            if section and section.is_active:
                return to_knowledge_section_entity(section)
            return None

    async def list_manipulations(self, section_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(KnowledgeManipulationModel)
                .where(
                    KnowledgeManipulationModel.section_id == section_id,
                    KnowledgeManipulationModel.is_active.is_(True),
                )
                .order_by(
                    KnowledgeManipulationModel.position,
                    KnowledgeManipulationModel.id,
                )
            )
            return [to_knowledge_manipulation_entity(item) for item in result.scalars().all()]

    async def get_manipulation(self, manipulation_id: int) -> KnowledgeManipulationEntity | None:
        async with async_session() as session:
            manipulation = await session.get(KnowledgeManipulationModel, manipulation_id)
            if manipulation and manipulation.is_active:
                return to_knowledge_manipulation_entity(manipulation)
            return None

    async def list_items(self, manipulation_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(KnowledgeItemModel)
                .where(KnowledgeItemModel.manipulation_id == manipulation_id)
                .order_by(KnowledgeItemModel.position, KnowledgeItemModel.id)
            )
            return [to_knowledge_item_entity(item) for item in result.scalars().all()]
