"""Ruff — lint + format for Python repos."""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import OFFENSES, OK, ToolResult, run

CAPABILITY = "style:ruff"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root)


def check(root: Path) -> ToolResult:
    return run("ruff", ["ruff", "check", "."], root)


def fix(root: Path) -> ToolResult:
    lint = run("ruff", ["ruff", "check", ".", "--fix"], root)
    fmt = run("ruff-format", ["ruff", "format", "."], root)
    if lint.failed or fmt.failed:
        return ToolResult("ruff", OFFENSES, lint.note or fmt.note)
    return ToolResult("ruff", OK)
