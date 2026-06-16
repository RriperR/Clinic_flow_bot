from app.application.admin.access_use_case import AdminAccessService
from app.application.admin.sync_use_case import AdminSyncService
from app.application.agent.catalog import build_tool_registry
from app.application.agent.prompts import AGENT_SYSTEM_PROMPT
from app.application.agent.use_case import AgentService
from app.application.instruments.admin_use_case import InstrumentAdminService
from app.application.instruments.transfer_use_case import InstrumentTransferService
from app.application.knowledge_base.use_case import KnowledgeBaseService
from app.application.llm.ports import LlmClient
from app.application.registration.use_case import RegistrationService
from app.application.reports.use_case import ReportsService
from app.application.reports.worker_report_use_case import WorkerReportService
from app.application.shifts.admin_use_case import ShiftAdminService
from app.application.shifts.use_case import ShiftService
from app.application.surveys.flow_use_case import SurveyFlowService
from app.application.surveys.scheduler_use_case import SurveyScheduler
from app.config import load_settings
from app.infrastructure.db.repositories import (
    SqlAlchemyAdminRepository,
    SqlAlchemyAnswerRepository,
    SqlAlchemyCabinetRepository,
    SqlAlchemyInstrumentMoveRepository,
    SqlAlchemyInstrumentRepository,
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyPairRepository,
    SqlAlchemyShiftRepository,
    SqlAlchemySurveyRepository,
    SqlAlchemyWorkerRepository,
)
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.llm.gateway import OpenAICompatibleLlmClient
from app.infrastructure.sheets.gateway import SheetsGateway
from app.presentation.reports.monthly_report_formatter import MonthlyReportTextRenderer


class Container:
    def __init__(self):
        self.settings = load_settings()

        # Infrastructure
        self.admin_repo = SqlAlchemyAdminRepository()
        self.worker_repo = SqlAlchemyWorkerRepository()
        self.pair_repo = SqlAlchemyPairRepository()
        self.survey_repo = SqlAlchemySurveyRepository()
        self.answer_repo = SqlAlchemyAnswerRepository()
        self.shift_repo = SqlAlchemyShiftRepository()
        self.cabinet_repo = SqlAlchemyCabinetRepository()
        self.instrument_repo = SqlAlchemyInstrumentRepository()
        self.instrument_move_repo = SqlAlchemyInstrumentMoveRepository()
        self.knowledge_base_repo = SqlAlchemyKnowledgeBaseRepository()

        self.sheets_gateway = SheetsGateway(self.settings.sheets)

        # Провайдер-агностичный LLM-клиент (модель/эндпоинт — из настроек).
        # Реализацию можно подменить здесь, не трогая прикладной слой (порт LlmClient).
        self.llm: LlmClient = OpenAICompatibleLlmClient(self.settings.llm)

        # Application layer
        self.registration = RegistrationService(self.worker_repo, self.sheets_gateway)
        self.knowledge_base = KnowledgeBaseService(
            self.knowledge_base_repo,
            self.sheets_gateway,
        )
        self.survey_flow = SurveyFlowService(
            self.worker_repo,
            self.pair_repo,
            self.survey_repo,
            self.answer_repo,
        )
        self.shift_service = ShiftService(self.worker_repo, self.shift_repo, SqlAlchemyUnitOfWork)
        self.shift_admin = ShiftAdminService(self.worker_repo, self.shift_repo)
        self.instrument_transfer = InstrumentTransferService(
            self.cabinet_repo,
            self.instrument_repo,
            self.instrument_move_repo,
        )
        self.instrument_admin = InstrumentAdminService(
            self.cabinet_repo,
            self.instrument_repo,
            self.instrument_move_repo,
        )
        self.admin_access = AdminAccessService(
            self.admin_repo,
            self.worker_repo,
            set(self.settings.bot.admin_chat_ids),
        )
        self.admin_sync = AdminSyncService(
            self.sheets_gateway,
            self.worker_repo,
            self.pair_repo,
            self.survey_repo,
            self.answer_repo,
            self.shift_repo,
            self.knowledge_base,
        )
        self.worker_report = WorkerReportService(self.worker_repo)
        self.reports = ReportsService(
            self.worker_repo,
            self.survey_repo,
            self.answer_repo,
            self.shift_repo,
            MonthlyReportTextRenderer(),
        )
        self.scheduler = SurveyScheduler(self.survey_flow)

        # Агент: ручной цикл tool-use поверх LLM-порта; тулы — read-only обёртки
        # над существующими use case. Логику ответов наращиваем сверху.
        self.agent = AgentService(
            self.llm,
            build_tool_registry(self.knowledge_base, self.shift_service),
            AGENT_SYSTEM_PROMPT,
        )


def build_container() -> Container:
    return Container()
