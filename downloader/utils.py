from __future__ import annotations

import logging
import re
from pathlib import Path

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE = re.compile(r"\s+")


def sanitize_filename(value: str, max_length: int = 100) -> str:
    cleaned = INVALID_FILENAME_CHARS.sub("_", value)
    cleaned = WHITESPACE.sub(" ", cleaned).strip(" ._")
    return (cleaned[:max_length].rstrip(" .") or "未命名")


def format_duration(seconds: float | int | None) -> str:
    if seconds is None:
        return "未知"
    total = max(0, int(seconds))
    minutes, second = divmod(total, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours:02d}:{minute:02d}:{second:02d}" if hours else f"{minute:02d}:{second:02d}"


def configure_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    # Redirect URLs can contain account/device identifiers and signed values.
    logging.getLogger("httpx").setLevel(logging.WARNING)
