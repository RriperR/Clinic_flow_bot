from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BASE_DIR / ".env"

# Приоритет источников (pydantic-settings): переменные окружения процесса >
# значения из .env > дефолты полей. Так shell-переменные перекрывают .env.
_BASE_CONFIG = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")


class BotSettings(BaseSettings):
    model_config = _BASE_CONFIG

    token: str = Field("", validation_alias="BOT_TOKEN")
    report_chat_id: str | None = Field(None, validation_alias="REPORT_CHAT_ID")
    # Список читаем как сырую строку и парсим в property: иначе pydantic-settings
    # пытается распарсить значение env как JSON.
    admin_chat_ids_raw: str = Field("", validation_alias="ADMIN_CHAT_IDS")

    @property
    def admin_chat_ids(self) -> list[str]:
        return [item.strip() for item in self.admin_chat_ids_raw.replace(";", ",").split(",") if item.strip()]


class DbSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", env_prefix="DB_", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    name: str = ""
    user: str = ""
    password: str = ""

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class SheetsSettings(BaseSettings):
    model_config = _BASE_CONFIG

    workers_sheet: str = Field("Список сотрудников", validation_alias="WORKERS_SHEET_NAME")
    pairs_sheet: str = Field("Пары сотрудников", validation_alias="PAIRS_SHEET_NAME")
    surveys_sheet: str = Field("Опросы", validation_alias="SURVEYS_SHEET_NAME")
    shifts_source_sheet: str = Field("Расписание смен", validation_alias="SHIFTS_SOURCE_SHEET_NAME")
    shift_report_sheet: str = Field("Отчёт по сменам", validation_alias="SHIFT_REPORT_SHEET_NAME")
    answers_sheet: str = Field("Ответы", validation_alias="ANSWERS_SHEET_NAME")
    main_table: str = Field("", validation_alias="TABLE")
    knowledge_table: str = Field("", validation_alias="KNOWLEDGE_TABLE")
    credentials_path: Path = _BASE_DIR / "q-bot-key2.json"

    @field_validator("main_table", "knowledge_table")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class LlmSettings(BaseSettings):
    # Провайдер-агностично: base_url выбирает провайдера (любой OpenAI-совместимый
    # эндпоинт), model — модель по умолчанию.
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", env_prefix="LLM_", extra="ignore")

    api_key: str = ""
    base_url: str = ""
    model: str = ""
    max_tokens: int = 1024
    timeout: float = 30

    @field_validator("base_url")
    @classmethod
    def _strip_slash(cls, value: str) -> str:
        return value.rstrip("/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    bot: BotSettings = Field(default_factory=BotSettings)
    db: DbSettings = Field(default_factory=DbSettings)
    sheets: SheetsSettings = Field(default_factory=SheetsSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    log_dir: Path = _BASE_DIR / "logs"


def load_settings() -> Settings:
    return Settings()
