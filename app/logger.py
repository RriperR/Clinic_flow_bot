import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = TimedRotatingFileHandler(
            filename=str(LOG_DIR / filename),
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
