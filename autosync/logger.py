"""
autosync/logger.py

Enterprise AutoSync Logger
"""

from pathlib import Path
import logging

from autosync.config import LOG_FILE


# ----------------------------------------------------
# Ensure log directory exists
# ----------------------------------------------------

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------
# Logger
# ----------------------------------------------------

logger = logging.getLogger("AutoSync")

logger.setLevel(logging.INFO)

logger.propagate = False


if not logger.handlers:

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8"
    )

    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()

    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


# ----------------------------------------------------
# Helper Functions
# ----------------------------------------------------

def info(message: str):
    logger.info(message)


def warning(message: str):
    logger.warning(message)


def error(message: str):
    logger.error(message)


def success(message: str):
    logger.info(f"SUCCESS: {message}")