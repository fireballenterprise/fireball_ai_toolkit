"""cargo test — the Rust workspace tests, always in release (debug is far slower for numeric code)."""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import ToolResult, run

CAPABILITY = "unit:cargo"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root)


def check(root: Path, *, scope: str | None = None) -> ToolResult:
    """`scope` filters by test name, as `cargo test <filter>` does."""
    return run("cargo-test", ["cargo", "test", "--workspace", "--release", *([scope] if scope else [])], root)
