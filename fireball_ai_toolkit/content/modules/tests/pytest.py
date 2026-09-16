"""pytest — the Python unit suite."""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import ToolResult, run

CAPABILITY = "unit:pytest"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root)


def check(root: Path, *, scope: str | None = None) -> ToolResult:
    cmd = ["pytest", "-m", scope] if scope else ["pytest"]
    return run("pytest", cmd, root)
