"""Render ``.sidecar/`` for Fireball Sidecar — instruction pointer stubs only.

Sidecar reads the canonical flat (or bundle) skills under ``.fireball_ai_toolkit/skills/`` and
``.<repo>/skills/`` directly, so it needs no generated skill or command views. A previous
version's ``.sidecar/commands/`` and ``.sidecar/skills/`` output is removed. Instructions keep
their pointer stubs (``name`` / ``description`` / ``applyTo``).
"""

from __future__ import annotations

from pathlib import Path

from ..catalog import ContentBundle
from ._common import canonical_pointer, clean_dir, remove_generated, write_doc


def render(bundle: ContentBundle, repo_root: Path) -> list[Path]:
    root = repo_root / ".sidecar"
    remove_generated(root / "commands")
    remove_generated(root / "skills")

    inst_dir = root / "instructions"
    inst_files = [
        write_doc(
            inst_dir / f"{i.slug}.md",
            canonical_pointer(bundle, i.slug, "instructions"),
            frontmatter={"name": i.slug, "description": i.description, "applyTo": i.apply_to},
        )
        for i in bundle.instructions
    ]
    clean_dir(inst_dir, inst_files)
    return inst_files
