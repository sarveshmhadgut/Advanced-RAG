"""
Configures application-wide logging with rotating file handlers.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.exception import MyException
from src.utils.time import get_current_timestamp

__all__: list[str] = ["config_logger", "get_current_timestamp", "logging"]

# Get root directory of the project
ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent
LOGS_DIR: str = "logs"


LOG_FILE_FORMAT: str = f"{get_current_timestamp()}.log"

maxBytes: int = 5 * 1024 * 1024  # 5 MB
backupCount: int = 4

try:
    logs_dirpath: str = os.path.join(str(ROOT_DIR), LOGS_DIR)
    os.makedirs(logs_dirpath, exist_ok=True)
    log_filepath: str = os.path.join(logs_dirpath, LOG_FILE_FORMAT)
except Exception as e:
    raise MyException(e, sys) from e


def config_logger() -> None:
    """
    Configures the global logging settings with a rotating file handler.

    Raises:
        MyException: If configuring the logger fails.
    """
    try:
        logger: logging.Logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        file_format: logging.Formatter = logging.Formatter(
            "[ %(asctime)s ] %(name)s - %(filename)s - %(levelname)s - %(message)s"
        )

        if not logger.handlers:
            file_handler: RotatingFileHandler = RotatingFileHandler(
                log_filepath,
                maxBytes=maxBytes,
                backupCount=backupCount,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)
    except Exception as e:
        raise MyException(e, sys) from e


config_logger()
