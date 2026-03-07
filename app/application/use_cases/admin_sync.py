from datetime import datetime

import re

from app.domain.entities import Worker, Pair, Survey
from app.domain.repositories import (
    WorkerRepository,
    PairRepository,
    SurveyRepository,
    AnswerRepository,
    ShiftRepository,
)
from app.infrastructure.sheets.gateway import SheetsGateway
from app.text_utils import normalize_text


class AdminSyncService:
    def __init__(
        self,
        gateway: SheetsGateway,
        workers: WorkerRepository,
        pairs: PairRepository,
        surveys: SurveyRepository,
        answers: AnswerRepository,
        shifts: ShiftRepository,
    ):
        self.gateway = gateway
        self.workers = workers
        self.pairs = pairs
        self.surveys = surveys
        self.answers = answers
        self.shifts = shifts

    async def sync_workers(self) -> int:
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
                id=None,
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

        return created

    async def sync_pairs(self, today_str: str | None = None) -> int:
        if not today_str:
            today_str = datetime.now().strftime("%d.%m.%Y")
        rows = self.gateway.read_pairs()
        created = 0
        for row in rows:
            if len(row) < 5 or row[4].strip() != today_str:
                continue
            pair = Pair(
                subject=row[0].strip(),
                object=row[1].strip(),
                survey=row[2].strip(),
                weekday=row[3].strip(),
                date=row[4].strip(),
            )
            await self.pairs.add(pair)
            created += 1
        return created

    async def sync_surveys(self) -> int:
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
        return created

    async def sync_shifts(self) -> int:
        rows = self.gateway.read_shifts()
        schedule: list[tuple[str, str, str, str | None, str | None, str | None]] = []
        for row in rows:
            if len(row) < 7:
                continue
            shift_code = row[1].strip()
            date = row[2].strip()
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
            if not doctor_name or not date:
                continue
            if assistant_planned == "-----------":
                assistant_planned = ""
            schedule.append(
                (
                    doctor_name,
                    date,
                    shift_type,
                    assistant_planned or None,
                    speciality or None,
                    cabinet or None,
                )
            )
        if schedule:
            await self.shifts.bulk_insert(schedule)
        return len(schedule)

    async def sync_all(self) -> None:
        await self.sync_workers()
        await self.sync_pairs()
        await self.sync_surveys()
        await self.sync_shifts()

    async def export_answers(self) -> None:
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

    async def export_shifts(self, date_str: str | None = None) -> None:
        if not date_str:
            date_str = datetime.now().strftime("%d.%m.%Y")
        shifts = await self.shifts.list_by_date(date_str)
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
                    shift.date,
                    shift_type,
                    shift.speciality or "",
                    shift.cabinet or "",
                    "Да" if shift.manual else "Нет",
                ]
                yield ["" if v is None else str(v) for v in row]

        self.gateway.export_shifts(headers, serialize())
