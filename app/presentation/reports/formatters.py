from app.application.reports.dto import WorkerShiftReport


def format_worker_shift_report(report: WorkerShiftReport) -> str:
    return (
        "📊 Отчёт по сменам\n"
        "(без учёта сегодняшних смен)\n\n"
        "🗓 За неделю:\n"
        f"• Всего смен: {report.shifts_week}\n"
        f"• Отдано смен: {report.given_week}\n"
        f"• Выходов на замену: {report.replacement_week}\n"
        f"• Смен выбрано вручную: {report.manual_week}\n\n"
        "📅 За месяц:\n"
        f"• Всего смен: {report.shifts_month}\n"
        f"• Отдано смен: {report.given_month}\n"
        f"• Выходов на замену: {report.replacement_month}\n"
        f"• Смен выбрано вручную: {report.manual_month}"
    )
