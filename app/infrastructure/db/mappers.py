from app.domain.entities import (
    AdminUser as AdminUserEntity,
    Answer as AnswerEntity,
    Cabinet as CabinetEntity,
    Instrument as InstrumentEntity,
    InstrumentMove as InstrumentMoveEntity,
    Pair as PairEntity,
    Shift as ShiftEntity,
    Survey as SurveyEntity,
    Worker as WorkerEntity,
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
)


def to_admin_entity(model: AdminUserModel | None) -> AdminUserEntity | None:
    if model is None:
        return None
    return AdminUserEntity(
        id=model.id,
        chat_id=model.chat_id,
        added_at=model.added_at,
    )


def from_admin_entity(entity: AdminUserEntity) -> AdminUserModel:
    return AdminUserModel(
        id=entity.id,
        chat_id=entity.chat_id,
        added_at=entity.added_at,
    )


def to_worker_entity(model: WorkerModel | None) -> WorkerEntity | None:
    if model is None:
        return None
    return WorkerEntity(
        id=model.id,
        full_name=model.full_name,
        file_id=model.file_id,
        chat_id=model.chat_id,
        speciality=model.speciality,
        phone=model.phone,
    )


def from_worker_entity(entity: WorkerEntity) -> WorkerModel:
    return WorkerModel(
        id=entity.id,
        full_name=entity.full_name,
        file_id=entity.file_id,
        chat_id=entity.chat_id,
        speciality=entity.speciality,
        phone=entity.phone,
    )


def to_pair_entity(model: PairModel | None) -> PairEntity | None:
    if model is None:
        return None
    return PairEntity(
        id=model.id,
        subject=model.subject,
        object=model.object,
        survey=model.survey,
        weekday=model.weekday,
        date=model.date,
        status=model.status,
    )


def from_pair_entity(entity: PairEntity) -> PairModel:
    return PairModel(
        id=entity.id,
        subject=entity.subject,
        object=entity.object,
        survey=entity.survey,
        weekday=entity.weekday,
        date=entity.date,
        status=entity.status,
    )


def to_survey_entity(model: SurveyModel | None) -> SurveyEntity | None:
    if model is None:
        return None
    return SurveyEntity(
        id=model.id,
        speciality=model.speciality,
        question1=model.question1,
        question1_type=model.question1_type,
        question2=model.question2,
        question2_type=model.question2_type,
        question3=model.question3,
        question3_type=model.question3_type,
        question4=model.question4,
        question4_type=model.question4_type,
        question5=model.question5,
        question5_type=model.question5_type,
    )


def from_survey_entity(entity: SurveyEntity) -> SurveyModel:
    return SurveyModel(
        id=entity.id,
        speciality=entity.speciality,
        question1=entity.question1,
        question1_type=entity.question1_type,
        question2=entity.question2,
        question2_type=entity.question2_type,
        question3=entity.question3,
        question3_type=entity.question3_type,
        question4=entity.question4,
        question4_type=entity.question4_type,
        question5=entity.question5,
        question5_type=entity.question5_type,
    )


def to_answer_entity(model: AnswerModel | None) -> AnswerEntity | None:
    if model is None:
        return None
    return AnswerEntity(
        id=model.id,
        subject=model.subject,
        object=model.object,
        survey=model.survey,
        survey_date=model.survey_date,
        completed_at=model.completed_at,
        question1=model.question1,
        answer1=model.answer1,
        question2=model.question2,
        answer2=model.answer2,
        question3=model.question3,
        answer3=model.answer3,
        question4=model.question4,
        answer4=model.answer4,
        question5=model.question5,
        answer5=model.answer5,
    )


def from_answer_entity(entity: AnswerEntity) -> AnswerModel:
    return AnswerModel(
        id=entity.id,
        subject=entity.subject,
        object=entity.object,
        survey=entity.survey,
        survey_date=entity.survey_date,
        completed_at=entity.completed_at,
        question1=entity.question1,
        answer1=entity.answer1,
        question2=entity.question2,
        answer2=entity.answer2,
        question3=entity.question3,
        answer3=entity.answer3,
        question4=entity.question4,
        answer4=entity.answer4,
        question5=entity.question5,
        answer5=entity.answer5,
    )


def to_shift_entity(model: ShiftModel | None) -> ShiftEntity | None:
    if model is None:
        return None
    return ShiftEntity(
        id=model.id,
        assistant_id=model.assistant_id,
        doctor_name=model.doctor_name,
        date=model.date,
        type=model.type,
        scheduled_assistant_name=model.scheduled_assistant_name,
        speciality=model.speciality,
        cabinet=model.cabinet,
        assistant_name=model.assistant_name,
        manual=model.manual,
    )


def from_shift_entity(entity: ShiftEntity) -> ShiftModel:
    return ShiftModel(
        id=entity.id,
        assistant_id=entity.assistant_id,
        doctor_name=entity.doctor_name,
        date=entity.date,
        type=entity.type,
        scheduled_assistant_name=entity.scheduled_assistant_name,
        speciality=entity.speciality,
        cabinet=entity.cabinet,
        assistant_name=entity.assistant_name,
        manual=entity.manual,
    )


def to_cabinet_entity(model: CabinetModel | None) -> CabinetEntity | None:
    if model is None:
        return None
    return CabinetEntity(
        id=model.id,
        name=model.name,
        is_active=model.is_active,
    )


def from_cabinet_entity(entity: CabinetEntity) -> CabinetModel:
    return CabinetModel(
        id=entity.id,
        name=entity.name,
        is_active=entity.is_active,
    )


def to_instrument_entity(model: InstrumentModel | None) -> InstrumentEntity | None:
    if model is None:
        return None
    return InstrumentEntity(
        id=model.id,
        name=model.name,
        cabinet_id=model.cabinet_id,
        is_active=model.is_active,
    )


def from_instrument_entity(entity: InstrumentEntity) -> InstrumentModel:
    return InstrumentModel(
        id=entity.id,
        name=entity.name,
        cabinet_id=entity.cabinet_id,
        is_active=entity.is_active,
    )


def to_instrument_move_entity(model: InstrumentMoveModel | None) -> InstrumentMoveEntity | None:
    if model is None:
        return None
    return InstrumentMoveEntity(
        id=model.id,
        instrument_id=model.instrument_id,
        from_cabinet_id=model.from_cabinet_id,
        to_cabinet_id=model.to_cabinet_id,
        before_photo_id=model.before_photo_id,
        after_photo_id=model.after_photo_id,
        moved_by_chat_id=model.moved_by_chat_id,
        moved_at=model.moved_at,
    )


def from_instrument_move_entity(entity: InstrumentMoveEntity) -> InstrumentMoveModel:
    return InstrumentMoveModel(
        id=entity.id,
        instrument_id=entity.instrument_id,
        from_cabinet_id=entity.from_cabinet_id,
        to_cabinet_id=entity.to_cabinet_id,
        before_photo_id=entity.before_photo_id,
        after_photo_id=entity.after_photo_id,
        moved_by_chat_id=entity.moved_by_chat_id,
        moved_at=entity.moved_at,
    )
