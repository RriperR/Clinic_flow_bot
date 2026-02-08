# Clinic Flow Bot

![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![aiogram](https://img.shields.io/badge/aiogram-latest-2C5E9E.svg)
![asyncio](https://img.shields.io/badge/asyncio-stdlib-9cf.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-async-red.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)
![Docker](https://img.shields.io/badge/docker-28.0-blue.svg)
![Google Sheets](https://img.shields.io/badge/Google%20Sheets-API-green.svg)
![APScheduler](https://img.shields.io/badge/APScheduler-latest-orange.svg)

Telegram-бот для клиники: регистрация сотрудников, опросы, учет смен и перемещения инструментов с фото. Работает асинхронно, данные хранятся в PostgreSQL, есть синхронизация с Google Sheets.

---

## Основные возможности

- Регистрация сотрудников и привязка chat id
- Опросы и выгрузка ответов в Google Sheets
- Смены: выбор из расписания и ручной ввод
- Перемещения инструментов между кабинетами с фото и журналом
- Админ-панель: кабинеты, инструменты, смены

---

## Структура проекта

```
Q_tg_bot/
├── app/
│   ├── bot.py               # Точка входа: инициализация бота, планировщика и логирования
│   ├── config.py            # Загрузка настроек из .env
│   ├── container.py         # DI-контейнер
│   ├── keyboards.py         # Inline-клавиатуры
│   ├── logger.py            # Логирование
│   ├── handlers/            # Telegram-команды и callback-обработчики
│   ├── application/
│   │   └── use_cases/       # Бизнес-логика
│   ├── domain/              # Сущности и интерфейсы репозиториев
│   └── infrastructure/
│       ├── db/              # SQLAlchemy модели, мапперы и репозитории
│       └── sheets/          # Доступ к Google Sheets
├── logs/                    # Логи (монтируются в Docker)
├── tests/                   # Тесты
├── docker-compose.yml       # Docker-сборка для бота и БД
├── Dockerfile               # Инструкция сборки образа бота
├── requirements.txt         # Зависимости проекта
└── README.md                # Документация
```

---

## Установка и запуск

1. Клонируйте репозиторий и перейдите в корень:

   ```bash
   git clone <repo_url>
   cd Q_tg_bot
   ```
2. Создайте виртуальное окружение и активируйте его:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```
4. Создайте файл `.env` с параметрами:

   ```env
   BOT_TOKEN=<your-telegram-token>
   DB_HOST=...
   DB_PORT=5432
   DB_NAME=...
   DB_USER=...
   DB_PASSWORD=...
   TABLE=<google_sheet-table-name>
   ANSWERS_TABLE=<google_sheet-table-name>
   REPORT_CHAT_ID=<tg-chat-id>
   ADMIN_CHAT_IDS=<optional, comma-separated>
   ```
5. Поместите `q-bot-key2.json` рядом с `.env`.
6. Запустите бота:

   ```bash
   python -m app.bot
   ```

---

## Слои приложения

- `domain/` — сущности и интерфейсы репозиториев.
- `application/use_cases/` — бизнес-логика (опросы, смены, инструменты, админ-доступ).
- `infrastructure/` — интеграции: БД и Google Sheets.
- `handlers/` — Telegram-команды и FSM-сценарии.

---

## Логирование

В `app/logger.py` используется функция `setup_logger(name, filename)`, которая настраивает:

- Уровень логгирования
- `TimedRotatingFileHandler` (ротация в полночь)
- Отдельные файлы для каждого модуля: `bot.log`, `reports.log`, `survey.log` и т.д.

В каждом модуле создается логгер:

```python
from app.logger import setup_logger
logger = setup_logger(__name__, "<module>.log")
```

---

## Docker и деплой

- `docker-compose.yml` поднимает бота и PostgreSQL.
- Логи монтируются в `logs/`.
- Планировщик (`apscheduler`) запускается вместе с ботом.
