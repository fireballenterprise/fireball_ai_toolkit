"""cargo-deny — Rust dependency licences, advisories, bans and sources, from the repo's `deny.toml`."""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import ToolResult, run

CAPABILITY = "style:cargo-deny"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root) and (root / "deny.toml").is_file()


def check(root: Path) -> ToolResult:
    return run("cargo-deny", ["cargo", "deny", "check"], root)
