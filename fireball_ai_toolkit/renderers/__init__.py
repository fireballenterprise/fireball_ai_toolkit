"""Per-tool renderers: each turns a :class:`~fireball_ai_toolkit.catalog.ContentBundle` into
the files one AI tool expects inside a consuming repo.

A renderer is a callable ``render(bundle, repo_root) -> list[Path]`` that writes its outputs and
returns the paths it wrote (so :mod:`fireball_ai_toolkit.render` and the drift check can diff
them). Every generated markdown file carries the :data:`~fireball_ai_toolkit.renderers._common.GENERATED_HEADER`
``DO NOT EDIT`` comment and is a pointer stub — the canonical source is ``.ai/toolkit/`` +
``.ai/<repo>/`` (``content/`` in this repo).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..catalog import ContentBundle
from . import agents, claude, cline, copilot, prompts, sidecar
from ._common import GENERATED_HEADER

Renderer = Callable[[ContentBundle, Path], list[Path]]

# Order is irrelevant — every renderer owns a disjoint set of output paths.
ALL: dict[str, Renderer] = {
    "agents": agents.render,
    "claude": claude.render,
    "cline": cline.render,
    "copilot": copilot.render,
    "prompts": prompts.render,
    "sidecar": sidecar.render,
}

__all__ = ["ALL", "GENERATED_HEADER", "Renderer"]
