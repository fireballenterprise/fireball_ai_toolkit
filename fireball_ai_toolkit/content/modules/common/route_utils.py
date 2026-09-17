"""Shared helpers for AI-tool command routing modules."""

from __future__ import annotations

import logging
import os
from pathlib import Path

LOGGER = logging.getLogger(__name__)


#: Set this to run a routed command against a different checkout than the current directory's
#: (e.g. a wrapper that targets another managed repo). find_repo_root() honours it before searching.
REPO_ROOT_ENV = "SIDECAR_REPO_ROOT"


def find_repo_root() -> Path:
    """Return the repo root: ``$SIDECAR_REPO_ROOT`` if set, else the nearest parent with properties.yml."""
    override = os.environ.get(REPO_ROOT_ENV)
    if override:
        return Path(override)
    current = Path.cwd()
    while current != current.parent:
        if (current / "properties.yml").exists():
            return current
        current = current.parent
    return Path.cwd()


def build_env(_repo_root: Path) -> dict[str, str]:
    """Build the subprocess environment for a routed command."""
    return os.environ.copy()


def peel_repo(args: list[str]) -> tuple[list[str], str | None]:
    """Pull a ``--repo <x>`` / ``--repo=<x>`` target selector out of ``args`` (any position).

    Returns ``(remaining_args, token_or_None)``. A router / task hands ``token`` to
    ``common.target_repo.resolve_target_repo`` and, when that returns a path, delegates the rest of
    ``remaining_args`` into the target checkout instead of running in-process.
    """
    out: list[str] = []
    token: str | None = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--repo":
            if index + 1 < len(args):
                token = args[index + 1]
                index += 2
                continue
            index += 1
            continue
        if arg.startswith("--repo="):
            token = arg.split("=", 1)[1]
            index += 1
            continue
        out.append(arg)
        index += 1
    return out, token
