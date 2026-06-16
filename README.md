# Clinic Flow Bot

![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![aiogram](https://img.shields.io/badge/aiogram-latest-2C5E9E.svg)
![asyncio](https://img.shields.io/badge/asyncio-stdlib-9cf.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-async-red.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)
![Docker](https://img.shields.io/badge/docker-28.0-blue.svg)
![Google Sheets](https://img.shields.io/badge/Google%20Sheets-API-green.svg)
![APScheduler](https://img.shields.io/badge/APScheduler-latest-orange.svg)

Telegram-бот для клиники. Он используется для регистрации сотрудников, выбора смен, отчётов по сменам, переноса инструментов между кабинетами и синхронизации рабочих данных с Google Sheets.

Основные сценарии:

- регистрация сотрудников и привязка Telegram-аккаунта
- выбор смены по расписанию и ручной выбор смены
- просмотр персонального отчёта по сменам
- просмотр базы знаний по команде `/base`
- перенос инструментов между кабинетами с фотофиксацией
- синхронизация сотрудников, смен и справочников с Google Sheets
- админские команды и Telegram-админка

## Что нужно для запуска

- Python `3.13`, если запускать без Docker
- Docker и Docker Compose, если запускать в контейнерах
- PostgreSQL
- Telegram bot token
- Google service account JSON с доступом к нужной таблице

Важно:

- файл сервисного аккаунта должен называться `q-bot-key2.json`
- файл должен лежать в корне проекта рядом с `docker-compose.yml`
- сервисному аккаунту нужно выдать доступ к Google-таблице, указанной в `TABLE`

## Структура проекта

```text
app/
  application/use_cases/   бизнес-логика
  domain/                  сущности и интерфейсы репозиториев
  handlers/                Telegram handlers
  infrastructure/db/       SQLAlchemy-модели, мапперы, репозитории
  infrastructure/sheets/   интеграция с Google Sheets
  bot.py                   точка входа
  config.py                чтение настроек из .env
  container.py             сборка зависимостей
tests/                     тесты
tools/                     вспомогательные скрипты
docker-compose.yml         локальный запуск бота и PostgreSQL
Dockerfile                 образ бота
requirements.txt           runtime-зависимости
```

## Быстрый старт в Docker

Это основной способ запуска проекта.

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd Q_tg_bot
```

### 2. Создать `.env`

Скопируй шаблон:

```bash
cp .env.example .env
```

На Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

### 3. Заполнить `.env`

Минимально нужно задать:

- `BOT_TOKEN`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `TABLE`

Для базы знаний отдельно:

- `KNOWLEDGE_TABLE`, если нужно включить синхронизацию базы знаний для команды `/base`

Для запуска через `docker compose` используй такие значения БД:

- `DB_HOST=db`
- `DB_PORT=5432`

`ADMIN_CHAT_IDS` указывается через запятую:

```env
ADMIN_CHAT_IDS=123456789,987654321
```

### 4. Положить Google credentials в корень проекта

В корне проекта должен лежать файл:

- `q-bot-key2.json`

Без него бот не сможет читать и обновлять Google Sheets.

### 5. Поднять контейнеры

```bash
docker compose up -d --build
```

После старта:

- поднимется контейнер `survey_db`
- поднимется контейнер `survey_bot`
- бот подключится к PostgreSQL
- таблицы в БД будут созданы при старте через `async_main()`
- зарегистрируются плановые задачи `APScheduler`

### 6. Проверить, что всё запустилось

Статус контейнеров:

```bash
docker compose ps
```

Логи бота:

```bash
docker compose logs -f bot
```

Логи базы:

```bash
docker compose logs -f db
```

## Полезные Docker-команды

Пересобрать и перезапустить проект:

```bash
docker compose up -d --build
```

Остановить контейнеры:

```bash
docker compose down
```

Остановить контейнеры и удалить volume базы:

```bash
docker compose down -v
```

Эту команду используй осторожно: `docker compose down -v` удаляет локальные данные PostgreSQL.

Если менялся только код внутри `app/`, обычно достаточно перезапустить бота:

```bash
docker compose restart bot
```

Если менялись зависимости, `Dockerfile`, `.env`, `docker-compose.yml` или `q-bot-key2.json`, нужна пересборка:

```bash
docker compose up -d --build
```

## Подключение к PostgreSQL с хоста

В `docker-compose.yml` база опубликована на `localhost:5435`.

Параметры подключения из DBeaver или другого клиента:

- host: `localhost`
- port: `5435`
- database: значение `DB_NAME` из `.env`
- user: значение `DB_USER` из `.env`
- password: значение `DB_PASSWORD` из `.env`

Важно: это порт для подключения с хостовой машины. Внутри docker-сети бот должен ходить в БД по `db:5432`.

## Запуск без Docker

Подходит для локальной разработки, если PostgreSQL уже доступен отдельно.

Самый простой вариант:

1. Поднять только базу через Docker.
2. Сам бот запускать локально из Python.

### 1. Поднять только PostgreSQL

```bash
docker compose up -d db
```

Тогда для локального запуска бота в `.env` используй:

```env
DB_HOST=localhost
DB_PORT=5435
```

### 2. Создать виртуальное окружение

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Применить миграции БД

Схему создаёт и обновляет Alembic (приложение больше не делает `create_all`):

```bash
make migrate          # alembic upgrade head
```

### 5. Запустить бота

```bash
python -m app.bot
```

## Миграции базы данных

Схема версионируется через Alembic (`migrations/`). URL подключения Alembic
берёт из тех же переменных `DB_*`, что и приложение.

```bash
make migrate                 # применить все миграции (alembic upgrade head)
make migrate-down            # откатить последнюю
make migration m="описание"  # сгенерировать ревизию из изменений моделей
```

### Внедрение на существующей (боевой) БД

Таблицы там уже созданы прежним `create_all`, поэтому базовую ревизию нужно
один раз «проштамповать», а не выполнять, иначе Alembic попытается создать
существующие таблицы:

```bash
make migrate-stamp           # alembic stamp 0001_baseline (разово)
make migrate                 # применит 0002 и последующие
```

### Миграция дат (0002)

`0002_normalize_dates` переводит строковые даты/время в `DATE`/`TIMESTAMP`.
Перед применением на проде сделайте бэкап и проверьте, что нет значений вне
ожидаемых форматов (`%d.%m.%Y` для дат) — иначе `ALTER` упадёт целиком.
Аудит-запросы и порядок выкатки описаны в `CONTRIBUTING.md`.

## Переменные окружения

### Обязательные

- `BOT_TOKEN` - токен Telegram-бота
- `DB_HOST` - хост PostgreSQL
- `DB_PORT` - порт PostgreSQL
- `DB_NAME` - имя базы
- `DB_USER` - пользователь базы
- `DB_PASSWORD` - пароль базы
- `TABLE` - имя основной Google-таблицы

### Необязательные, но обычно используются

- `REPORT_CHAT_ID` - чат для сервисных уведомлений и отчётов
- `ADMIN_CHAT_IDS` - список chat_id админов через запятую
- `KNOWLEDGE_TABLE` - отдельная Google-таблица для базы знаний
- `WORKERS_SHEET_NAME` - лист сотрудников
- `PAIRS_SHEET_NAME` - лист с парами сотрудников
- `SURVEYS_SHEET_NAME` - лист опросов
- `SHIFTS_SOURCE_SHEET_NAME` - лист-источник расписания смен
- `SHIFT_REPORT_SHEET_NAME` - лист выгрузки отчёта по сменам
- `ANSWERS_SHEET_NAME` - лист ответов, если эта интеграция используется в текущей ветке

Полный шаблон есть в [.env.example](/d:/PyProjects/Q_tg_bot/.env.example).

## Как работает интеграция с Google Sheets

Бот берёт имя основной таблицы из `TABLE`. Имена листов читаются из `.env`, а если переменные не заданы, используются значения по умолчанию из [app/config.py](/d:/PyProjects/Q_tg_bot/app/config.py).

Для базы знаний используется отдельная таблица `KNOWLEDGE_TABLE`.

- если `KNOWLEDGE_TABLE` задана, база знаний синхронизируется из этой таблицы в PostgreSQL по расписанию
- команда `/base` открывает разделы базы знаний из PostgreSQL, без запроса к Google Sheets на каждый клик
- вручную обновить кэш можно командой `/upd_knowledge`
- если `KNOWLEDGE_TABLE` не задана, команда `/base` отвечает, что база знаний не настроена

Файл сервисного аккаунта читается из фиксированного пути в корне проекта:

- [q-bot-key2.json](/d:/PyProjects/Q_tg_bot/q-bot-key2.json)

Если бот не видит таблицу, почти всегда проблема в одном из трёх мест:

- файла `q-bot-key2.json` нет в корне проекта
- сервисному аккаунту не выдан доступ к таблице
- в `TABLE` указано неверное имя Google-таблицы

Если не работает именно `/base`, отдельно проверь `KNOWLEDGE_TABLE`, доступ сервисного аккаунта к этой таблице и наличие данных в таблицах `knowledge_sections`, `knowledge_manipulations`, `knowledge_items`.

## Планировщик

Cron-задачи регистрируются в [app/bot.py](/d:/PyProjects/Q_tg_bot/app/bot.py).

Сейчас приложение поднимает планировщик при старте и автоматически запускает фоновые задачи, например:

- синхронизацию сотрудников
- синхронизацию базы знаний
- синхронизацию смен
- экспорт смен в Google Sheets

Если меняется расписание фоновых задач, править нужно именно `app/bot.py`.

## Логирование

Файлы логов создаются в директории `logs/`:

- `bot.log` - запуск, остановка и системные события бота
- `actions.log` - действия пользователей: команды, callback-кнопки, фото и другие входящие события
- `errors.log` - непойманные ошибки с traceback и кодом ошибки

Если задан `REPORT_CHAT_ID`, бот отправляет в этот чат уведомления о пользовательских действиях и ошибках. В Telegram-уведомлениях есть ФИО сотрудника из БД при наличии, действие и статус. `chat_id`, username, длительность обработки и технические детали остаются только в файловых логах. Тексты обычных сообщений и `file_id` фотографий в Telegram-лог не отправляются.

## Частые проблемы

### Бот не стартует и ругается на Google Sheets

Проверь:

- существует ли `q-bot-key2.json`
- открыт ли доступ сервисному аккаунту к Google-таблице
- корректно ли заполнен `TABLE`

### Бот не подключается к базе

Проверь:

- поднят ли контейнер `db`
- совпадают ли `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- правильный ли `DB_HOST`
- не перепутаны ли `5432` внутри Docker и `5435` на хосте

### После изменения кода в Docker ничего не поменялось

Пересобери проект:

```bash
docker compose up -d --build
```

Если менялся только код внутри `app/`, сначала попробуй `docker compose restart bot`.

Если менялся `q-bot-key2.json`, зависимости или `Dockerfile`, нужна именно пересборка, потому что эти изменения попадают в контейнер не через bind mount, а через сборку образа.

## Чеклист для нового разработчика

1. Склонировать репозиторий.
2. Создать `.env` из `.env.example`.
3. Положить `q-bot-key2.json` в корень проекта.
4. Выдать сервисному аккаунту доступ к нужной Google-таблице.
5. Заполнить `BOT_TOKEN` и параметры БД.
6. Выполнить `docker compose up -d --build`.
7. Проверить `docker compose logs -f bot`.

Если бот запустился без ошибок, окружение собрано правильно.
