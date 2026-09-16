"""Android Lint — AGP's built-in checks (resources, API levels, manifest)."""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import ToolResult, gradlew

CAPABILITY = "style:android-lint"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root)


def check(root: Path) -> ToolResult:
    return gradlew(root, ["lint"], name="android-lint")
