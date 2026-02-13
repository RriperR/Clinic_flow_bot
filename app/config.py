import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class BotSettings:
    token: str
    report_chat_id: str | None
    admin_chat_ids: list[str]


@dataclass
class DbSettings:
    host: str
    port: str
    name: str
    user: str
    password: str


@dataclass
class SheetsSettings:
    credentials_path: Path
    workers_sheet: str
    pairs_sheet: str
    surveys_sheet: str
    shifts_source_sheet: str
    shift_report_sheet: str
    answers_sheet: str
    main_table: str


@dataclass
class Settings:
    bot: BotSettings
    db: DbSettings
    sheets: SheetsSettings
    log_dir: Path


def load_settings() -> Settings:
    load_dotenv()

    base_dir = Path(__file__).resolve().parent.parent
    log_dir = (base_dir / "logs").resolve()
    credentials_path = (base_dir / "q-bot-key2.json").resolve()

    sheets = SheetsSettings(
        credentials_path=credentials_path,
        workers_sheet=os.getenv("WORKERS_SHEET_NAME", "Список сотрудников"),
        pairs_sheet=os.getenv("PAIRS_SHEET_NAME", "Пары сотрудников"),
        surveys_sheet=os.getenv("SURVEYS_SHEET_NAME", "Опросы"),
        shifts_source_sheet=os.getenv("SHIFTS_SOURCE_SHEET_NAME", "Расписание смен"),
        shift_report_sheet=os.getenv("SHIFT_REPORT_SHEET_NAME", "Отчёт по сменам"),
        answers_sheet=os.getenv("ANSWERS_SHEET_NAME", "Ответы"),
        main_table=os.getenv("TABLE", ""),
    )

    db = DbSettings(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        name=os.getenv("DB_NAME", ""),
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
    )

    bot = BotSettings(
        token=os.getenv("BOT_TOKEN", ""),
        report_chat_id=os.getenv("REPORT_CHAT_ID"),
        admin_chat_ids=[
            item.strip()
            for item in os.getenv("ADMIN_CHAT_IDS", "").replace(";", ",").split(",")
            if item.strip()
        ],
    )

    return Settings(
        bot=bot,
        db=db,
        sheets=sheets,
        log_dir=log_dir,
    )
