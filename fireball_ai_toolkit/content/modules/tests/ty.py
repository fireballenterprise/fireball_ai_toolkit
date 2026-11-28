"""ty — the Python type checker (config from pyproject.toml ``[tool.ty]``), part of ``tests.style``.

Runs when ``ty`` is installed in the repo's environment (a dev dependency pinned under the dependency age rule); a repo without it
skips it, like every other tool.
"""

from __future__ import annotations

from pathlib import Path

from ..common import toolchains
from .common import ToolResult, run

CAPABILITY = "style:ty"


def applies(root: Path) -> bool:
    return CAPABILITY in toolchains.capabilities(root)


def check(root: Path) -> ToolResult:
    return run("ty", ["ty", "check"], root)
