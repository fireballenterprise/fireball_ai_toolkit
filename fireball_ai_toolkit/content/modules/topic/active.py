"""Track the currently active topic in active_topic.yml at the repo root.

Schema ported from `fireball_ai_vault`'s `template_ai_vault` lineage (2026-08-09) — a header
comment + `---` document-start marker (fixes the yamllint "missing document start" warning the
old bare `topic: <path>` form triggered) plus `current_topic`/`base_path`/`switched_at`, richer
than this repo's original single-field version. `base_path` is written for parity with that
format (and as a convenience for anything that wants the `topics/`-prefixed form without
recomputing it) but isn't read back by anything here — `current_topic` plus `get_repo_root()` is
always the derived source of truth, same "paths stay portable across machines" reasoning
`fireball_ai_vault`'s own version documents.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import yaml

from ..setup.properties import get_repo_root

LOGGER = logging.getLogger(__name__)

_ACTIVE_TOPIC_FILE = "active_topic.yml"
_HEADER = "# Active topic tracker\n# Managed by topic/switch.py\n# Do not edit manually\n---\n"


def _active_topic_path() -> Path:
    return get_repo_root() / _ACTIVE_TOPIC_FILE


def get_active_topic() -> str | None:
    """Return the currently active topic path (relative to topics/), or None if unset."""
    path = _active_topic_path()
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text()) or {}
    return data.get("current_topic")


def set_active_topic(topic_path: str) -> None:
    """Record `topic_path` as the active topic, with the timestamp of this switch."""
    data = {
        "current_topic": topic_path,
        "base_path": f"topics/{topic_path}",
        "switched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _active_topic_path().write_text(_HEADER + yaml.safe_dump(data, sort_keys=False))


def clear_active_topic() -> None:
    """Remove the active-topic tracker, if present."""
    path = _active_topic_path()
    if path.exists():
        path.unlink()
