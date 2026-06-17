from collections import defaultdict

PERIOD_LABELS = {
    "Month": "за месяц",
    "Half-year": "за полгода",
    "All time": "за всё время",
}


class MonthlyReportTextRenderer:
    def format_report(self, results, open_answers, shifts_info=None) -> list[str]:
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

            period_label = PERIOD_LABELS.get(period_name, period_name)
            text = f"Результаты опросов — {period_label}:\n\n"

            for survey_title, questions in surveys.items():
                text += f"— Опрос: {survey_title}\n"
                for question, scores in questions.items():
                    avg = round(sum(scores) / len(scores), 2)
                    text += f"• {question}\n {avg} / 5 (оценок: {len(scores)})\n\n"

            if period_name == "Month" and open_answers:
                text += "— Открытые ответы:\n"
                for survey_title, qa_pairs in open_answers.items():
                    grouped = defaultdict(list)
                    for question, answer in qa_pairs:
                        grouped[question.strip()].append(answer.strip())

                    text += f"\nОпрос: {survey_title}\n"
                    for question, answers in grouped.items():
                        text += f"{question}\n"
                        for ans in answers:
                            text += f"    - {ans}\n"
                        text += "\n"

            if period_name == "Month" and shifts_info:
                text += "\n— Смены, где помогал(а) в этом месяце:\n"
                for doctor, count in shifts_info.items():
                    text += f"  {doctor} — смен: {count}\n"

            messages.append(text.strip())

        return messages
