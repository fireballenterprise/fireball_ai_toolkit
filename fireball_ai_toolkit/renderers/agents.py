"""Render the repo-root entrypoints.

* ``AGENTS.md`` — the tool-neutral **index**: a short preamble, one bullet per instruction linking
  to its canonical ``.fireball_ai_toolkit/`` (or ``.<repo>/``) file, and the source-of-truth note.
* ``CLAUDE.md`` — a fixed short pointer to ``AGENTS.md``.
"""

from __future__ import annotations

from pathlib import Path

from ..catalog import ContentBundle
from ._common import write_doc

_PREAMBLE = (
    "This repo's rules for any AI coding tool are authored once under `.fireball_ai_toolkit/` (synced from "
    "`fireball_ai_toolkit`) and `.{local}/` (this repo's own). Every `.github/`, `.claude/`, "
    "`.clinerules/`, and `.sidecar/` file is a generated pointer back to them. Read the relevant "
    "canonical file before making changes:"
)

_SOURCE_OF_TRUTH = (
    "**Source of truth: `.fireball_ai_toolkit/` and `.{local}/`** — all rules, slash commands, and skills "
    "live there as tool-neutral markdown. Never hand-edit a generated provider file "
    "(`.github/`, `.claude/`, `.clinerules/`, `.sidecar/`, `AGENTS.md`, `CLAUDE.md`); edit the "
    "`.fireball_ai_toolkit/` source and run `invoke ai_toolkit.apply`."
)

_CLAUDE_MD = """# Claude Code Instructions

See `AGENTS.md` for all instructions — it links to every canonical file under `.fireball_ai_toolkit/` and
`.{local}/`, the source of truth for this repo's rules, slash commands, and skills.

{source_of_truth}
"""


def _canonical(bundle: ContentBundle, slug: str) -> str:
    if bundle.is_local(slug):
        return f".{bundle.local_name}/instructions/{slug}.md"
    return f".fireball_ai_toolkit/instructions/{slug}.md"


def render(bundle: ContentBundle, repo_root: Path) -> list[Path]:
    local = bundle.local_name
    source_of_truth = _SOURCE_OF_TRUTH.format(local=local)
    bullets = "\n".join(f"- **{i.label}**: `{_canonical(bundle, i.slug)}`" for i in bundle.instructions)
    agents_body = f"# Agent Instructions\n\n{_PREAMBLE.format(local=local)}\n\n{bullets}\n\n{source_of_truth}"
    claude_md = _CLAUDE_MD.format(local=local, source_of_truth=source_of_truth)
    return [
        write_doc(repo_root / "AGENTS.md", agents_body),
        write_doc(repo_root / "CLAUDE.md", claude_md),
    ]
