from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.application.reports.ports import MessageSender
from app.domain.repositories import (
    AnswerRepository,
    ShiftRepository,
    SurveyRepository,
    WorkerRepository,
)
from app.logger import setup_logger


class ReportsService:
    def __init__(
        self,
        workers: WorkerRepository,
        surveys: SurveyRepository,
        answers: AnswerRepository,
        shifts: ShiftRepository,
    ):
        self.workers = workers
        self.surveys = surveys
        self.answers = answers
        self.shifts = shifts
        self.logger = setup_logger("reports", "reports.log")

    async def send_monthly_reports(self, sender: MessageSender) -> None:
        self.logger.info("Starting monthly reports generation")
        now = datetime.now(ZoneInfo("Europe/Moscow"))

        workers = list(await self.workers.list_all())
        answers = list(await self.answers.list_all())
        shifts = list(await self.shifts.list_all())

        surveys_by_name = await self._collect_survey_cache(answers)
        answers_by_object = self._group_answers_by_object(answers)
        shifts_by_assistant = self._group_shifts_last_month(shifts, now)

        sent_count = 0
        skipped_count = 0

        for worker in workers:
            worker_answers = answers_by_object.get(worker.full_name, [])
            worker_shifts = shifts_by_assistant.get(worker.id)

            if not worker_answers and not worker_shifts:
                skipped_count += 1
                self.logger.debug("Skip report: no data for %s", worker.full_name)
                continue

            results, open_answers = self._calculate_scores_for_worker(worker_answers, surveys_by_name, now)

            try:
                messages = self._format_report_text(
                    results,
                    open_answers,
                    worker_shifts,
                )
                for message in messages:
                    await self._safe_send_long_message(sender, worker.chat_id, message)
                self.logger.info("Report sent: %s (%s)", worker.full_name, worker.chat_id)
                sent_count += 1
            except Exception as exc:
                self.logger.error(
                    "Failed to send report %s (%s): %s",
                    worker.full_name,
                    worker.chat_id,
                    exc,
                )

        self.logger.info(
            "Reports done. Sent: %s, skipped: %s",
            sent_count,
            skipped_count,
        )

    # --- helpers ---
    async def _collect_survey_cache(self, all_answers):
        survey_names = set(ans.survey for ans in all_answers)
        surveys_by_name = {}
        for name in survey_names:
            surveys_by_name[name] = await self.surveys.get_by_name(name)
        return surveys_by_name

    def _group_answers_by_object(self, all_answers):
        grouped = defaultdict(list)
        for ans in all_answers:
            grouped[ans.object].append(ans)
        return grouped

    def _group_shifts_last_month(self, all_shifts, now: datetime):
        one_month_ago = now - timedelta(days=30)
        result = defaultdict(lambda: defaultdict(int))
        for shift in all_shifts:
            if shift.assistant_id is None:
                continue
            shift_date = self._parse_russian_date(shift.date)
            if not shift_date or shift_date < one_month_ago:
                continue
            result[shift.assistant_id][shift.doctor_name] += 1
        return result

    def _calculate_scores_for_worker(self, answers, surveys_by_name, now: datetime):
        one_month_ago = now - timedelta(days=30)
        six_months_ago = now - timedelta(days=180)

        results = {
            "Month": defaultdict(lambda: defaultdict(list)),
            "Half-year": defaultdict(lambda: defaultdict(list)),
            "All time": defaultdict(lambda: defaultdict(list)),
        }

        open_answers = defaultdict(list)

        for ans in answers:
            survey = surveys_by_name.get(ans.survey)
            if not survey:
                continue

            survey_date = self._parse_russian_date(ans.survey_date)
            if not survey_date:
                continue

            for i in range(1, 5 + 1):
                question_text = getattr(survey, f"question{i}", f"Question {i}").split("\n")[0]
                q_type = getattr(survey, f"question{i}_type")

                raw_answer = getattr(ans, f"answer{i}")
                if q_type == "int":
                    try:
                        score = int(raw_answer)
                        if not (1 <= score <= 5):
                            continue
                    except (ValueError, TypeError):
                        continue

                    if survey_date >= one_month_ago:
                        results["Month"][survey.speciality][question_text].append(score)
                    if survey_date >= six_months_ago:
                        results["Half-year"][survey.speciality][question_text].append(score)
                    results["All time"][survey.speciality][question_text].append(score)

                elif q_type == "str" and survey_date >= one_month_ago:
                    if raw_answer and str(raw_answer).strip():
                        open_answers[survey.speciality].append((question_text, str(raw_answer).strip()))

        return results, open_answers

    def _format_report_text(self, results, open_answers, shifts_info=None):
        messages = []
        period_values_seen = set()

        for period_name, surveys in results.items():
            serialized = str(
                sorted(
                    (survey, question, sorted(scores))
                    for survey, questions in surveys.items()
                    for question, scores in questions.items()
                )
            )

            has_scores = bool(surveys)
            has_month_extras = period_name == "Month" and (open_answers or shifts_info)
            if not has_scores and not has_month_extras:
                continue
            if has_scores and serialized in period_values_seen:
                continue
            if has_scores:
                period_values_seen.add(serialized)

            text = f"Survey results — {period_name}:\n\n"

            for survey_title, questions in surveys.items():
                text += f"— Survey: {survey_title}\n"
                for question, scores in questions.items():
                    avg = round(sum(scores) / len(scores), 2)
                    text += f"• {question}\n {avg} / 5 ({len(scores)} answers)\n\n"

            if period_name == "Month" and open_answers:
                text += "— Open answers:\n"
                for survey_title, qa_pairs in open_answers.items():
                    grouped = defaultdict(list)
                    for question, answer in qa_pairs:
                        grouped[question.strip()].append(answer.strip())

                    text += f"\nSurvey: {survey_title}\n"
                    for question, answers in grouped.items():
                        text += f"{question}\n"
                        for ans in answers:
                            text += f"    - {ans}\n"
                        text += "\n"

            if period_name == "Month" and shifts_info:
                text += "\n— Shifts helped with this month:\n"
                for doctor, count in shifts_info.items():
                    text += f"  {doctor} — {count} shift(s)\n"

            messages.append(text.strip())

        return messages

    def _parse_russian_date(self, date_str: str):
        try:
            return datetime.strptime(date_str, "%d.%m.%Y").replace(tzinfo=ZoneInfo("Europe/Moscow"))
        except Exception:
            return None

    def _split_message(self, text: str, max_len: int = 4096):
        lines = text.split("\n")
        chunks = []
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 < max_len:
                current += line + "\n"
            else:
                chunks.append(current.strip())
                current = line + "\n"
        if current:
            chunks.append(current.strip())
        return chunks

    async def _safe_send_long_message(
        self,
        sender: MessageSender,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
    ):
        for part in self._split_message(text):
            await sender.send_message(chat_id=chat_id, text=part, parse_mode=parse_mode)
