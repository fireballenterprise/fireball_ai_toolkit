"""Track each topic's currently active chat in its own active.yml."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

LOGGER = logging.getLogger(__name__)


def _active_chat_path(topic_dir: Path) -> Path:
    return topic_dir / "active.yml"


def get_active_chat(topic_dir: Path) -> dict[str, str] | None:
    """Return the active chat's tracked fields for `topic_dir`, or None if none is active."""
    path = _active_chat_path(topic_dir)
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text()) or None


def set_active_chat(
    topic_dir: Path,
    *,
    filename: str,
    title: str,
    started: str,
    topic: str,
    status: str = "active",
) -> None:
    """Record the active chat's tracked fields for `topic_dir`."""
    data = {"filename": filename, "title": title, "started": started, "topic": topic, "status": status}
    _active_chat_path(topic_dir).write_text(yaml.safe_dump(data, sort_keys=False))


def clear_active_chat(topic_dir: Path) -> None:
    """Remove the active-chat tracker for `topic_dir`, if present."""
    path = _active_chat_path(topic_dir)
    if path.exists():
        path.unlink()
