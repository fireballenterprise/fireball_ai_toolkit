"""ktlint — Kotlin style / format (via the Gradle plugin)."""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import ToolResult, gradlew

CAPABILITY = "style:ktlint"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root)


def check(root: Path) -> ToolResult:
    return gradlew(root, ["ktlintCheck"], name="ktlint")


def fix(root: Path) -> ToolResult:
    return gradlew(root, ["ktlintFormat"], name="ktlint")
