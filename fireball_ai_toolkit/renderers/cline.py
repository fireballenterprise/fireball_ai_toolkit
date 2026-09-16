"""Render ``.clinerules/workflows/*.md`` for Cline — pointer stubs.

Cline workflows are body-only (no frontmatter). Each is a one-line pointer at the canonical
``.ai/toolkit|local/commands/<slug>.md``.
"""

from __future__ import annotations

from pathlib import Path

from ..catalog import ContentBundle
from ._common import canonical_pointer, clean_dir, write_doc


def render(bundle: ContentBundle, repo_root: Path) -> list[Path]:
    out_dir = repo_root / ".clinerules" / "workflows"
    written = [
        write_doc(out_dir / f"{c.slug}.md", canonical_pointer(bundle, c.slug, "commands")) for c in bundle.commands
    ]
    clean_dir(out_dir, written)
    return written
