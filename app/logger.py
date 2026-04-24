import asyncio
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from aiogram import Bot

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
TELEGRAM_FORMAT = "%(levelname)s - %(name)s - %(message)s"

_telegram_handler: "TelegramQueueLogHandler | None" = None


class TelegramQueueLogHandler(logging.Handler):
    def __init__(
        self,
        bot: Bot,
        chat_id: str,
        *,
        level: int = logging.INFO,
        queue_size: int = 1000,
    ):
        super().__init__(level=level)
        self.bot = bot
        self.chat_id = chat_id
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=queue_size)
        self.task: asyncio.Task | None = None
        self.fallback_logger = setup_logger("telegram_logs", "bot.log")

    def start(self) -> None:
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._send_loop())

    async def stop(self) -> None:
        if not self.task:
            return
        try:
            await asyncio.wait_for(self.queue.join(), timeout=3)
        except asyncio.TimeoutError:
            self.fallback_logger.warning("Telegram log queue drain timed out")
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = getattr(record, "telegram_message", None) or self.format(record)
            self.queue.put_nowait(message[:4096])
        except asyncio.QueueFull:
            self.fallback_logger.warning("Telegram log queue is full; message dropped")
        except Exception:
            self.handleError(record)

    async def _send_loop(self) -> None:
        while True:
            message = await self.queue.get()
            try:
                await self.bot.send_message(chat_id=self.chat_id, text=message)
            except Exception as exc:
                self.fallback_logger.error("Failed to send log to Telegram: %s", exc)
            finally:
                self.queue.task_done()


class TelegramReportFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return bool(getattr(record, "send_to_telegram", False))


def setup_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not _has_file_handler(logger, filename):
        handler = TimedRotatingFileHandler(
            filename=str(LOG_DIR / filename),
            when="midnight",
            interval=1,
            backupCount=14,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handler._qbot_filename = filename
        logger.addHandler(handler)

    return logger


def setup_telegram_logging(bot: Bot, report_chat_id: str | None) -> None:
    global _telegram_handler

    if not report_chat_id:
        return

    if _telegram_handler is None:
        _telegram_handler = TelegramQueueLogHandler(bot, report_chat_id)
        _telegram_handler.setFormatter(logging.Formatter(TELEGRAM_FORMAT))
        _telegram_handler.addFilter(TelegramReportFilter())
        _telegram_handler.start()

    for logger_name in ("bot", "actions", "errors"):
        logger = logging.getLogger(logger_name)
        if not _has_handler(logger, _telegram_handler):
            logger.addHandler(_telegram_handler)


async def shutdown_telegram_logging() -> None:
    if _telegram_handler:
        await _telegram_handler.stop()


def _has_file_handler(logger: logging.Logger, filename: str) -> bool:
    return any(
        isinstance(handler, TimedRotatingFileHandler)
        and getattr(handler, "_qbot_filename", None) == filename
        for handler in logger.handlers
    )


def _has_handler(logger: logging.Logger, expected: logging.Handler) -> bool:
    return any(handler is expected for handler in logger.handlers)
