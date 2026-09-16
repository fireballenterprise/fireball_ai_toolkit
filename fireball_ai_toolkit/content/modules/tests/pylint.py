"""Pylint — static analysis for Python repos (config from pyproject.toml)."""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import ToolResult, run

CAPABILITY = "style:pylint"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root)


def check(root: Path) -> ToolResult:
    return run("pylint", ["pylint", "--rcfile=pyproject.toml", "."], root)
