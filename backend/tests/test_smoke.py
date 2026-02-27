"""Smoke tests for boot-time failures not caught by unit tests."""

import importlib
import logging


def test_configure_logging_json():
    from app.logging_config import configure_logging
    configure_logging(json_logs=True)


def test_configure_logging_console():
    from app.logging_config import configure_logging
    configure_logging(json_logs=False)


def test_get_logger_returns_usable_logger():
    from app.logging_config import configure_logging, get_logger
    configure_logging(json_logs=False, log_level="WARNING")
    logger = get_logger("smoke")
    logger.info("smoke test log message")


def test_worker_imports():
    import worker  # noqa: F401


def test_app_main_imports():
    importlib.import_module("app.main")


def test_app_validators_imports():
    importlib.import_module("app.validators")


def test_app_repositories_imports():
    importlib.import_module("app.repositories")


def test_app_models_imports():
    importlib.import_module("app.models")


def test_app_config_imports():
    importlib.import_module("app.config")


def test_app_utils_imports():
    importlib.import_module("app.utils")
