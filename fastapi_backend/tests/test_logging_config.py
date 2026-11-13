import logging
from unittest.mock import Mock

import pytest

from app import logging_config


@pytest.mark.parametrize(
    ("app_env", "vercel"),
    [("development", True), ("production", False)],
)
def test_serverless_logging_does_not_create_files_or_directories(
    monkeypatch, app_env: str, vercel: bool
) -> None:
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    root.handlers.clear()
    mkdir = Mock()
    file_handler = Mock(side_effect=AssertionError("file logging must be disabled"))
    monkeypatch.setattr(logging_config.Path, "mkdir", mkdir)
    monkeypatch.setattr(logging_config, "RotatingFileHandler", file_handler)
    if vercel:
        monkeypatch.setenv("VERCEL", "1")
    else:
        monkeypatch.delenv("VERCEL", raising=False)

    try:
        logging_config.configure_logging(app_env)

        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], logging.StreamHandler)
        assert not isinstance(root.handlers[0], logging.FileHandler)
        mkdir.assert_not_called()
        file_handler.assert_not_called()
    finally:
        root.handlers.clear()
        root.handlers.extend(original_handlers)
        root.setLevel(original_level)
