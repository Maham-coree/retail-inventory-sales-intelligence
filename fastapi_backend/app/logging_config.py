"""Console and rotating-file logging configuration."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(app_env: str = "development") -> None:
    root = logging.getLogger()
    production = "VERCEL" in os.environ or app_env.lower() == "production"
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    if production:
        for handler in root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                root.removeHandler(handler)
                handler.close()
        console_handlers = [
            handler
            for handler in root.handlers
            if isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, logging.FileHandler)
        ]
        if not console_handlers:
            console_handlers = [logging.StreamHandler()]
            root.addHandler(console_handlers[0])
        for handler in console_handlers:
            handler.setFormatter(formatter)
        root.setLevel(logging.INFO)
        return

    if root.handlers:
        return

    log_dir = Path(__file__).resolve().parents[1] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.setLevel(logging.INFO)
    root.addHandler(console)
    root.addHandler(file_handler)
