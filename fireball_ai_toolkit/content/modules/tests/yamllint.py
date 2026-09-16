"""yamllint — YAML style for any repo with YAML outside .github/workflows."""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import ToolResult, run

CAPABILITY = "style:yamllint"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root)


def check(root: Path) -> ToolResult:
    cmd = ["yamllint", "."]
    if (root / ".yamllint").exists():
        cmd = ["yamllint", "-c", ".yamllint", "."]
    return run("yamllint", cmd, root)
