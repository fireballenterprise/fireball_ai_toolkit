"""Render ``.github/prompts/*.prompt.md`` — the GitHub.com prompt-file picker view.

A pointer stub: full frontmatter (``name``/``description``/``argument-hint``/``agent``) + a
one-line pointer at the canonical ``.ai/toolkit|local/commands/<slug>.md``.
"""

from __future__ import annotations

from pathlib import Path

from ..catalog import ContentBundle
from ._common import canonical_pointer, clean_dir, write_doc


def render(bundle: ContentBundle, repo_root: Path) -> list[Path]:
    out_dir = repo_root / ".github" / "prompts"
    written = [
        write_doc(
            out_dir / f"{command.slug}.prompt.md",
            canonical_pointer(bundle, command.slug, "commands"),
            frontmatter={
                "name": command.slug,
                "description": command.description,
                "argument-hint": command.argument_hint,
                "agent": command.agent,
            },
        )
        for command in bundle.commands
    ]
    clean_dir(out_dir, written)
    return written
