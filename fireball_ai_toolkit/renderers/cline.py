"""Render ``.clinerules/workflows/*.md`` for Cline — pointer stubs.

Cline workflows are body-only (no frontmatter). Skills are the slash commands, so each skill
gets one workflow: a one-line pointer at the canonical ``.fireball_ai_toolkit|local/skills/<slug>.md``.
Skills with ``user-invocable: false`` are skipped.
"""

from __future__ import annotations

from pathlib import Path

from ..catalog import ContentBundle
from ._common import canonical_pointer, clean_dir, write_doc


def render(bundle: ContentBundle, repo_root: Path) -> list[Path]:
    out_dir = repo_root / ".clinerules" / "workflows"
    written = [
        write_doc(out_dir / f"{s.name}.md", canonical_pointer(bundle, s.name, "skills"))
        for s in bundle.skills
        if s.user_invocable
    ]
    clean_dir(out_dir, written)
    return written
