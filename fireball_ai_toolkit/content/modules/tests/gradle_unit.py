"""Gradle unit tests — the Kotlin/JVM debug unit suite."""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import ToolResult, gradlew

CAPABILITY = "unit:gradle"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root)


def check(root: Path, *, scope: str | None = None) -> ToolResult:  # noqa: ARG001 - scope is pytest-only
    return gradlew(root, ["testDebugUnitTest"], name="gradle-unit")
