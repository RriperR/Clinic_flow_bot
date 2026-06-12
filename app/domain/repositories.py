from app.domain.admin.repositories import AdminRepository
from app.domain.instruments.repositories import CabinetRepository, InstrumentMoveRepository, InstrumentRepository
from app.domain.knowledge_base.repositories import KnowledgeBaseRepository
from app.domain.shifts.repositories import ShiftRepository
from app.domain.surveys.repositories import AnswerRepository, PairRepository, SurveyRepository
from app.domain.workers.repositories import WorkerRepository

__all__ = [
    "AdminRepository",
    "AnswerRepository",
    "CabinetRepository",
    "InstrumentMoveRepository",
    "InstrumentRepository",
    "KnowledgeBaseRepository",
    "PairRepository",
    "ShiftRepository",
    "SurveyRepository",
    "WorkerRepository",
]
