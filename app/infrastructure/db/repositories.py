from sqlalchemy import select, update, delete

from app.domain.entities import AdminUser as AdminUserEntity
from app.domain.entities import Worker as WorkerEntity
from app.domain.entities import Pair as PairEntity
from app.domain.entities import Survey as SurveyEntity
from app.domain.entities import Answer as AnswerEntity
from app.domain.entities import Shift as ShiftEntity
from app.domain.entities import Cabinet as CabinetEntity
from app.domain.entities import Instrument as InstrumentEntity
from app.domain.entities import InstrumentMove as InstrumentMoveEntity
from app.domain.repositories import (
    AdminRepository,
    WorkerRepository,
    PairRepository,
    SurveyRepository,
    AnswerRepository,
    ShiftRepository,
    CabinetRepository,
    InstrumentRepository,
    InstrumentMoveRepository,
)
from app.infrastructure.db.mappers import (
    from_admin_entity,
    from_answer_entity,
    from_cabinet_entity,
    from_instrument_entity,
    from_instrument_move_entity,
    from_pair_entity,
    from_shift_entity,
    from_survey_entity,
    from_worker_entity,
    to_admin_entity,
    to_answer_entity,
    to_cabinet_entity,
    to_instrument_entity,
    to_instrument_move_entity,
    to_pair_entity,
    to_shift_entity,
    to_survey_entity,
    to_worker_entity,
)
from app.infrastructure.db.models import (
    AdminUser as AdminUserModel,
    Answer as AnswerModel,
    Cabinet as CabinetModel,
    Instrument as InstrumentModel,
    InstrumentMove as InstrumentMoveModel,
    Pair as PairModel,
    Shift as ShiftModel,
    Survey as SurveyModel,
    Worker as WorkerModel,
    async_session,
)


class SqlAlchemyAdminRepository(AdminRepository):
    async def list_all(self):
        async with async_session() as session:
            result = await session.execute(
                select(AdminUserModel).order_by(AdminUserModel.chat_id)
            )
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
            stmt = select(AdminUserModel.id).where(
                AdminUserModel.chat_id == admin.chat_id
            )
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
    async def get_by_fullname(self, full_name: str) -> WorkerEntity | None:
        async with async_session() as session:
            stmt = select(WorkerModel).where(WorkerModel.full_name == full_name)
            result = await session.execute(stmt)
            return to_worker_entity(result.scalar_one_or_none())

    async def get_by_chat_id(self, chat_id: int) -> WorkerEntity | None:
        async with async_session() as session:
            stmt = select(WorkerModel).where(WorkerModel.chat_id == str(chat_id))
            result = await session.execute(stmt)
            return to_worker_entity(result.scalar_one_or_none())

    async def get_by_id(self, worker_id: int) -> WorkerEntity | None:
        async with async_session() as session:
            stmt = select(WorkerModel).where(WorkerModel.id == worker_id)
            result = await session.execute(stmt)
            return to_worker_entity(result.scalar_one_or_none())

    async def list_all(self):
        async with async_session() as session:
            result = await session.execute(select(WorkerModel))
            return [to_worker_entity(item) for item in result.scalars().all()]

    async def list_unregistered(self):
        async with async_session() as session:
            stmt = select(WorkerModel).where(
                (WorkerModel.chat_id.is_(None)) | (WorkerModel.chat_id == "")
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

            stmt = (
                update(WorkerModel)
                .where(WorkerModel.id == worker_id)
                .values(chat_id=chat_id)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def set_file_id(self, worker_id: int, file_id: str) -> None:
        async with async_session() as session:
            worker = await session.get(WorkerModel, worker_id)
            if worker:
                worker.file_id = file_id
                await session.commit()


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
            await session.commit()


class SqlAlchemyPairRepository(PairRepository):
    async def list_ready_by_date(self, date: str):
        async with async_session() as session:
            stmt = (
                select(PairModel)
                .where(PairModel.status == "ready", PairModel.date <= date)
                .order_by(PairModel.id)
            )
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
            stmt = (
                update(PairModel)
                .where(PairModel.id == pair_id)
                .values(status=status)
            )
            await session.execute(stmt)
            await session.commit()

    async def reset_incomplete(self) -> None:
        async with async_session() as session:
            stmt = (
                update(PairModel)
                .where(PairModel.status == "in_progress")
                .values(status="ready")
            )
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
    async def clear_all(self) -> None:
        async with async_session() as session:
            await session.execute(delete(ShiftModel))
            await session.commit()

    async def bulk_insert(
        self, records: list[tuple[str, str, str, str | None, str | None, str | None]]
    ) -> None:
        async with async_session() as session:
            for (
                doctor_name,
                date,
                shift_type,
                scheduled_assistant_name,
                speciality,
                cabinet,
            ) in records:
                session.add(
                    ShiftModel(
                        doctor_name=doctor_name,
                        date=date,
                        type=shift_type,
                        scheduled_assistant_name=scheduled_assistant_name,
                        speciality=speciality,
                        cabinet=cabinet,
                        manual=False,
                    )
                )
            await session.commit()

    async def list_free(self, date: str, shift_type: str) -> list[tuple[int, str]]:
        async with async_session() as session:
            result = await session.execute(
                select(ShiftModel.id, ShiftModel.doctor_name).where(
                    ShiftModel.date == date,
                    ShiftModel.type == shift_type,
                    ShiftModel.assistant_id.is_(None),
                )
            )
            return [(row.id, row.doctor_name) for row in result.all()]

    async def get_by_id(self, shift_id: int) -> ShiftEntity | None:
        async with async_session() as session:
            shift = await session.get(ShiftModel, shift_id)
            return to_shift_entity(shift)

    async def get_for_assistant(self, assistant_id: int, date: str, shift_type: str) -> ShiftEntity | None:
        async with async_session() as session:
            result = await session.execute(
                select(ShiftModel).where(
                    ShiftModel.assistant_id == assistant_id,
                    ShiftModel.date == date,
                    ShiftModel.type == shift_type,
                )
            )
            return to_shift_entity(result.scalar_one_or_none())

    async def remove_assistant(self, assistant_id: int, date: str, shift_type: str) -> None:
        async with async_session() as session:
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
            await session.commit()

    async def add_by_id(self, assistant_id: int, assistant_name: str, shift_id: int) -> bool:
        async with async_session() as session:
            shift = await session.get(ShiftModel, shift_id)
            if not shift or shift.assistant_id is not None:
                return False

            already_stmt = await session.execute(
                select(ShiftModel).where(
                    ShiftModel.assistant_id == assistant_id,
                    ShiftModel.date == shift.date,
                    ShiftModel.type == shift.type,
                )
            )
            if already_stmt.scalar_one_or_none():
                return False

            shift.assistant_id = assistant_id
            shift.assistant_name = assistant_name
            shift.manual = False
            await session.commit()
            return True

    async def add_manual(
        self,
        assistant_id: int,
        assistant_name: str,
        doctor_name: str,
        shift_type: str,
        date: str,
    ) -> bool:
        async with async_session() as session:
            already = await session.execute(
                select(ShiftModel).where(
                    ShiftModel.assistant_id == assistant_id,
                    ShiftModel.date == date,
                    ShiftModel.type == shift_type,
                )
            )
            if already.scalar_one_or_none():
                return False

            shift = ShiftModel(
                assistant_id=assistant_id,
                assistant_name=assistant_name,
                doctor_name=doctor_name,
                type=shift_type,
                date=date,
                manual=True,
            )
            session.add(shift)
            await session.commit()
            return True

    async def add_slot(self, doctor_name: str, date: str, shift_type: str) -> bool:
        async with async_session() as session:
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
            await session.commit()
            return True

    async def delete_by_id(self, shift_id: int) -> bool:
        async with async_session() as session:
            shift = await session.get(ShiftModel, shift_id)
            if not shift:
                return False
            await session.delete(shift)
            await session.commit()
            return True

    async def list_by_date(self, date: str):
        async with async_session() as session:
            result = await session.execute(
                select(ShiftModel).where(ShiftModel.date == date)
            )
            return [to_shift_entity(item) for item in result.scalars().all()]

    async def list_all(self):
        async with async_session() as session:
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
                select(InstrumentModel.id)
                .where(InstrumentModel.cabinet_id == cabinet_id)
                .limit(1)
            )
            return result.scalar_one_or_none() is not None


class SqlAlchemyInstrumentRepository(InstrumentRepository):
    async def list_by_cabinet(self, cabinet_id: int, include_archived: bool = False):
        async with async_session() as session:
            stmt = (
                select(InstrumentModel)
                .where(InstrumentModel.cabinet_id == cabinet_id)
                .order_by(InstrumentModel.name)
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
                select(InstrumentMoveModel)
                .order_by(InstrumentMoveModel.id.desc())
                .limit(limit)
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
