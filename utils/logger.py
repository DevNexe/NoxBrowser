"""
utils/logger.py

Централизованная настройка логирования.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_configured = False


def _configure_logging() -> None:
    global _configured
    if _configured:
        return

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
    ]

    log_dir = Path.home() / ".cef_browser" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        file_handler = logging.FileHandler(log_dir / "browser.log", encoding="utf-8")
        handlers.append(file_handler)
    except OSError:
        pass

    logging.basicConfig(
        level=logging.DEBUG,
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
    )

    # Снижаем шум от Qt/CEF
    logging.getLogger("cefpython3").setLevel(logging.WARNING)
    logging.getLogger("PySide6").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_logging()
    return logging.getLogger(name)
