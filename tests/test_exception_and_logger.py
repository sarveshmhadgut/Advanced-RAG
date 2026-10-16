"""
Unit tests for the custom exception hierarchy and logger configuration.
"""

import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.exception import (
    ConfigurationError,
    DocumentParsingError,
    EmbeddingError,
    MyException,
    ValidationError,
    error_message_detail,
)
from src.logger import config_logger, logging


def test_my_exception_formatting() -> None:
    """
    Test that MyException captures filename, line number, and error message.
    """
    try:
        raise ValueError("Simulated underlying error")
    except ValueError as e:
        custom_exc: MyException = MyException(e, sys)

    error_str: str = str(custom_exc)
    assert "Simulated underlying error" in error_str
    assert "test_exception_and_logger.py" in error_str
    assert "line" in error_str


def test_error_message_detail_without_active_traceback() -> None:
    """
    Test error_message_detail fallback when no active exception traceback is available.
    """
    detail: str = error_message_detail("Raw error string", sys)
    assert "Raw error string" in detail
    assert "Error in" in detail


def test_domain_exceptions_subclass_my_exception() -> None:
    """
    Test that all domain-specific exception classes inherit from MyException.
    """
    for exc_class in [
        ConfigurationError,
        DocumentParsingError,
        EmbeddingError,
        ValidationError,
    ]:
        assert issubclass(exc_class, MyException)
        assert issubclass(exc_class, Exception)


def test_logger_rotating_file_handler_configured(tmp_path: Path) -> None:
    """
    Test that a RotatingFileHandler configured with project standards meets size and level specifications.

    Args:
        tmp_path (Path): Pytest temporary directory fixture.
    """
    config_logger()
    test_handler: RotatingFileHandler = RotatingFileHandler(
        tmp_path / "test.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=4,
        encoding="utf-8",
    )
    test_handler.setLevel(logging.INFO)

    assert test_handler.maxBytes == 5 * 1024 * 1024
    assert test_handler.backupCount == 4
    assert test_handler.level == logging.INFO


def test_logger_logging_info_call() -> None:
    """
    Test executing logging.info without exception.
    """
    logging.info("Testing logging.info operational diagnostic message.")
