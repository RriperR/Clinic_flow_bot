import re
from datetime import date, datetime, timedelta

from app.application.admin.ports import AdminSyncGateway
from app.application.knowledge_base.use_case import KnowledgeBaseService
from app.domain.entities import Pair, Survey, Worker
from app.domain.repositories import (
    AnswerRepository,
    PairRepository,
    ShiftRepository,
    SurveyRepository,
    WorkerRepository,
)
from app.domain.shifts.value_objects import format_shift_date, parse_shift_date, ShiftImportRow
from app.logger import setup_logger
from app.text_utils import normalize_text

logger = setup_logger("bot", "bot.log")


class AdminSyncService:
    def __init__(
        self,
        gateway: AdminSyncGateway,
        workers: WorkerRepository,
        pairs: PairRepository,
        surveys: SurveyRepository,
        answers: AnswerRepository,
        shifts: ShiftRepository,
        knowledge_base: KnowledgeBaseService | None = None,
    ):
        self.gateway = gateway
        self.workers = workers
        self.pairs = pairs
        self.surveys = surveys
        self.answers = answers
        self.shifts = shifts
        self.knowledge_base = knowledge_base

    async def sync_workers(self) -> int:
        self._log_job_event("sync_workers", "start")
        try:
            def read_metric(row: list[str], index: int) -> int:
                if index >= len(row):
                    return 0
                raw = row[index].strip().replace(" ", "")
                if not raw:
                    return 0
                if raw.isdigit():
                    return int(raw)
                match = re.search(r"\d+", raw)
                return int(match.group(0)) if match else 0

            existing = {
                normalize_text(w.full_name): w
                for w in await self.workers.list_all(include_inactive=True)
                if w.full_name
            }
            rows = self.gateway.read_workers()
            created = 0
            seen: set[str] = set()

            for row in rows:
                full_name = row[0].strip() if len(row) > 0 else ""
                if not full_name:
                    continue
                key = normalize_text(full_name)
                seen.add(key)
                file_id = row[1].strip() if len(row) > 1 else ""
                chat_id = row[2].strip() if len(row) > 2 else ""
                speciality = row[3].strip() if len(row) > 3 else ""
                phone = row[4].strip() if len(row) > 4 else ""
                shifts_week = read_metric(row, 5)
                shifts_month = read_metric(row, 6)
                given_week = read_metric(row, 7)
                given_month = read_metric(row, 8)
                replacement_week = read_metric(row, 9)
                replacement_month = read_metric(row, 10)
                manual_week = read_metric(row, 11)
                manual_month = read_metric(row, 12)

                worker = existing.get(key)
                if worker:
                    if worker.id is None:
                        continue
                    if worker.chat_id and not chat_id:
                        logger.warning(
                            "sync_workers clears chat_id from empty Google Sheets value: "
                            "worker_id=%s full_name=%s old_chat_id=%s",
                            worker.id,
                            worker.full_name,
                            worker.chat_id,
                        )
                    await self.workers.update_from_sync(
                        worker.id,
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
                        is_active=True,
                    )
                    continue

                new_worker = Worker(
                    full_name=full_name,
                    file_id=file_id,
                    chat_id=chat_id,
                    speciality=speciality,
                    phone=phone,
                    shifts_week=shifts_week,
                    shifts_month=shifts_month,
                    given_week=given_week,
                    given_month=given_month,
                    replacement_week=replacement_week,
                    replacement_month=replacement_month,
                    manual_week=manual_week,
                    manual_month=manual_month,
                )
                await self.workers.add(new_worker)
                created += 1

            for key, worker in existing.items():
                if key in seen:
                    continue
                if worker.is_active and worker.id is not None:
                    await self.workers.set_active(worker.id, False)

            self._log_job_event("sync_workers", "ok", f"new={created}")
            return created
        except Exception as exc:
            self._log_job_event("sync_workers", "error", f"{type(exc).__name__}: {exc}")
            raise

    async def sync_pairs(self, today: date | None = None) -> int:
        self._log_job_event("sync_pairs", "start")
        try:
            if today is None:
                today = datetime.now().date()
            rows = self.gateway.read_pairs()
            created = 0
            for row in rows:
                if len(row) < 5:
                    continue
                try:
                    row_date = parse_shift_date(row[4].strip())
                except ValueError:
                    continue
                if row_date != today:
                    continue
                pair = Pair(
                    subject=row[0].strip(),
                    object=row[1].strip(),
                    survey=row[2].strip(),
                    weekday=row[3].strip(),
                    date=row_date,
                )
                await self.pairs.add(pair)
                created += 1
            self._log_job_event("sync_pairs", "ok", f"new={created}")
            return created
        except Exception as exc:
            self._log_job_event("sync_pairs", "error", f"{type(exc).__name__}: {exc}")
            raise

    async def sync_surveys(self) -> int:
        self._log_job_event("sync_surveys", "start")
        try:
            rows = self.gateway.read_surveys()
            await self.surveys.clear_all()
            created = 0
            for row in rows:
                id_value = row[0].strip() if row else ""
                if not id_value.isdigit():
                    continue
                survey = Survey(
                    id=int(id_value),
                    speciality=row[1].strip(),
                    question1=row[2].strip(),
                    question1_type=row[3].strip(),
                    question2=row[4].strip(),
                    question2_type=row[5].strip(),
                    question3=row[6].strip(),
                    question3_type=row[7].strip(),
                    question4=row[8].strip(),
                    question4_type=row[9].strip(),
                    question5=row[10].strip(),
                    question5_type=row[11].strip(),
                )
                await self.surveys.add(survey)
                created += 1
            self._log_job_event("sync_surveys", "ok", f"new={created}")
            return created
        except Exception as exc:
            self._log_job_event("sync_surveys", "error", f"{type(exc).__name__}: {exc}")
            raise

    async def sync_shifts(self) -> int:
        self._log_job_event("sync_shifts", "start")
        try:
            rows = self.gateway.read_shifts()
            schedule: list[ShiftImportRow] = []
            for row in rows:
                if len(row) < 7:
                    continue
                shift_code = row[1].strip()
                date_str = row[2].strip()
                doctor_name = row[3].strip()
                assistant_planned = row[4].strip()
                speciality = row[5].strip()
                cabinet = row[6].strip()
                if shift_code == "1":
                    shift_type = "morning"
                elif shift_code == "2":
                    shift_type = "evening"
                else:
                    continue
                if not doctor_name or not date_str:
                    continue
                try:
                    shift_date = parse_shift_date(date_str)
                except ValueError:
                    continue
                if assistant_planned == "-----------":
                    assistant_planned = ""
                schedule.append(
                    ShiftImportRow(
                        doctor_name=doctor_name,
                        date=shift_date,
                        type=shift_type,
                        scheduled_assistant_name=assistant_planned or None,
                        speciality=speciality or None,
                        cabinet=cabinet or None,
                    )
                )
            if schedule:
                await self.shifts.bulk_insert(schedule)
            self._log_job_event("sync_shifts", "ok", f"rows={len(schedule)}")
            return len(schedule)
        except Exception as exc:
            self._log_job_event("sync_shifts", "error", f"{type(exc).__name__}: {exc}")
            raise

    async def sync_all(self) -> None:
        await self.sync_workers()
        await self.sync_pairs()
        # await self.sync_surveys()
        await self.sync_shifts()
        await self.sync_knowledge_base()

    async def sync_knowledge_base(self) -> int:
        self._log_job_event("sync_knowledge_base", "start")
        try:
            if not self.knowledge_base:
                self._log_job_event("sync_knowledge_base", "ok", "disabled")
                return 0
            count = await self.knowledge_base.sync_from_sheets()
            self._log_job_event("sync_knowledge_base", "ok", f"items={count}")
            return count
        except Exception as exc:
            self._log_job_event("sync_knowledge_base", "error", f"{type(exc).__name__}: {exc}")
            raise

    async def export_answers(self) -> None:
        self._log_job_event("export_answers", "start")
        try:
            answers = await self.answers.list_all()
            headers = [
                "object",
                "subject",
                "survey",
                "survey_date",
                "completed_at",
                "question1",
                "answer1",
                "question2",
                "answer2",
                "question3",
                "answer3",
                "question4",
                "answer4",
                "question5",
                "answer5",
            ]

            def serialize():
                for ans in answers:
                    row = [getattr(ans, f, "") for f in headers]
                    yield ["" if cell is None else str(cell) for cell in row]

            self.gateway.export_answers(headers, serialize())
            self._log_job_event("export_answers", "ok", f"rows={len(answers)}")
        except Exception as exc:
            self._log_job_event("export_answers", "error", f"{type(exc).__name__}: {exc}")
            raise

    async def export_shifts(self, target_date: date | None = None) -> None:
        self._log_job_event("export_shifts", "start")
        try:
            if target_date is None:
                target_date = (datetime.now() - timedelta(days=1)).date()
            shifts = await self.shifts.list_by_date(target_date)
            headers = [
                "doctor_name",
                "scheduled_assistant_name",
                "assistant_name",
                "date",
                "type",
                "speciality",
                "cabinet",
                "manual",
            ]

            def serialize():
                for shift in shifts:
                    shift_type = shift.type
                    if shift_type == "morning":
                        shift_type = "утренняя"
                    elif shift_type == "evening":
                        shift_type = "вечерняя"
                    row = [
                        shift.doctor_name,
                        shift.scheduled_assistant_name or "",
                        shift.assistant_name or "",
                        format_shift_date(shift.date),
                        shift_type,
                        shift.speciality or "",
                        shift.cabinet or "",
                        "Да" if shift.manual else "Нет",
                    ]
                    yield ["" if v is None else str(v) for v in row]

            self.gateway.export_shifts(headers, serialize())
            self._log_job_event("export_shifts", "ok", f"rows={len(shifts)} date={format_shift_date(target_date)}")
        except Exception as exc:
            self._log_job_event("export_shifts", "error", f"{type(exc).__name__}: {exc}")
            raise

    def _log_job_event(self, job_name: str, status: str, details: str | None = None) -> None:
        icons = {
            "start": "🔄",
            "ok": "✅",
            "error": "❌",
        }
        icon = icons.get(status, "ℹ️")
        file_message = f"{job_name} status={status}"
        if details:
            file_message += f" {details}"
        telegram_lines = [
            f"{icon} {job_name}",
            f"статус: {status}",
        ]
        if details:
            telegram_lines.append(details)
        logger.info(
            file_message,
            extra={
                "send_to_telegram": True,
                "telegram_message": "\n".join(telegram_lines),
            },
        )
