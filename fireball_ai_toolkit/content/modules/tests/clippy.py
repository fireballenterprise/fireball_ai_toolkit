"""clippy — the Rust linter, every warning an error (the repo's `clippy.toml` and `[workspace.lints]` pick the rules)."""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import ToolResult, run

CAPABILITY = "style:clippy"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root)


def check(root: Path) -> ToolResult:
    return run("clippy", ["cargo", "clippy", "--workspace", "--all-targets", "--", "-D", "warnings"], root)


def fix(root: Path) -> ToolResult:
    return run(
        "clippy", ["cargo", "clippy", "--workspace", "--all-targets", "--fix", "--allow-dirty", "--allow-staged"], root
    )
