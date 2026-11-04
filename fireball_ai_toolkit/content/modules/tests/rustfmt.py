"""rustfmt — Rust formatting (`cargo fmt`), configured by the repo's `rustfmt.toml`."""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import ToolResult, run

CAPABILITY = "style:rustfmt"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root)


def check(root: Path) -> ToolResult:
    return run("rustfmt", ["cargo", "fmt", "--all", "--", "--check"], root)


def fix(root: Path) -> ToolResult:
    return run("rustfmt", ["cargo", "fmt", "--all"], root)
