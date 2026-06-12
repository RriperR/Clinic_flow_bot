from app.application.reports.dto import WorkerShiftReport


def format_worker_shift_report(report: WorkerShiftReport) -> str:
    return (
        "рџ“Љ РћС‚С‡С‘С‚ РїРѕ СЃРјРµРЅР°Рј\n"
        "(Р±РµР· СѓС‡С‘С‚Р° СЃРµРіРѕРґРЅСЏС€РЅРёС… СЃРјРµРЅ)\n\n"
        "рџ—“ Р—Р° РЅРµРґРµР»СЋ:\n"
        f"вЂў Р’СЃРµРіРѕ СЃРјРµРЅ: {report.shifts_week}\n"
        f"вЂў РћС‚РґР°РЅРѕ СЃРјРµРЅ: {report.given_week}\n"
        f"вЂў Р’С‹С…РѕРґРѕРІ РЅР° Р·Р°РјРµРЅСѓ: {report.replacement_week}\n"
        f"вЂў РЎРјРµРЅ РІС‹Р±СЂР°РЅРѕ РІСЂСѓС‡РЅСѓСЋ: {report.manual_week}\n\n"
        "рџ“… Р—Р° РјРµСЃСЏС†:\n"
        f"вЂў Р’СЃРµРіРѕ СЃРјРµРЅ: {report.shifts_month}\n"
        f"вЂў РћС‚РґР°РЅРѕ СЃРјРµРЅ: {report.given_month}\n"
        f"вЂў Р’С‹С…РѕРґРѕРІ РЅР° Р·Р°РјРµРЅСѓ: {report.replacement_month}\n"
        f"вЂў РЎРјРµРЅ РІС‹Р±СЂР°РЅРѕ РІСЂСѓС‡РЅСѓСЋ: {report.manual_month}"
    )
