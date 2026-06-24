import logging
import sys
from app.core.config import settings

_FMT = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _fh(filename: str) -> logging.FileHandler:
    h = logging.FileHandler(settings.LOGS_DIR / filename, encoding="utf-8")
    h.setFormatter(_FMT)
    return h


def _sh() -> logging.StreamHandler:
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(_FMT)
    return h


def get_logger(name: str, log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    logger.addHandler(_fh(log_file))
    logger.addHandler(_sh())
    logger.propagate = False
    return logger


app_logger     = get_logger("techpulse.app",     "app.log")
crawler_logger = get_logger("techpulse.crawler", "crawler.log")
error_logger   = get_logger("techpulse.error",   "error.log", logging.ERROR)