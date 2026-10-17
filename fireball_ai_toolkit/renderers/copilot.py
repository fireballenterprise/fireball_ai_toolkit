"""Render GitHub Copilot / VS Code files — all pointer stubs.

* ``.github/instructions/<slug>.instructions.md`` — ``description`` + ``applyTo`` frontmatter and a
  one-line pointer at the canonical ``.fireball_ai_toolkit|local/instructions/<slug>.md``. Copilot's
  ``applyTo`` auto-injection then delivers the pointer; whether Copilot follows it to the real
  rules is a known tradeoff of the pointer-only model.
* ``.github/copilot-instructions.md`` — the always-on index.
* ``.github/skills/<name>/SKILL.md`` — the Agent Skills runtime (VS Code, Copilot CLI/app): invoked
  as ``/<name>`` or loaded by the AI. Frontmatter ``name`` (== folder), ``description``,
  ``argument-hint``, ``user-invocable`` / ``disable-model-invocation`` (always explicit); body
  the full skill text. A bundle's extra resource files are copied alongside.
* A previous version's generated ``.github/prompts/*.prompt.md`` files are removed.
"""

from __future__ import annotations

from pathlib import Path

from ..catalog import ContentBundle
from ._common import canonical_pointer, clean_dir, remove_generated, render_skill_folders, write_doc

_INDEX = """# Copilot Instructions

See `AGENTS.md` at the repo root for the project overview and the instruction-file map. The
canonical rules and skills live under `.fireball_ai_toolkit/` (from `fireball_ai_toolkit`) and
`.{local}/` (this repo's own). Everything under `.github/instructions/*.instructions.md`
auto-applies by its `applyTo` glob and points back there. Skills are in `.github/skills/<name>/SKILL.md`:
call one as `/<name>` in chat, or let Copilot load it when its description matches. Never hand-edit a
generated file.
"""


def render(bundle: ContentBundle, repo_root: Path) -> list[Path]:
    github = repo_root / ".github"

    inst_dir = github / "instructions"
    written = [
        write_doc(
            inst_dir / f"{i.slug}.instructions.md",
            canonical_pointer(bundle, i.slug, "instructions"),
            frontmatter={"description": i.description, "applyTo": i.apply_to},
        )
        for i in bundle.instructions
    ]
    clean_dir(inst_dir, written)

    written.append(write_doc(github / "copilot-instructions.md", _INDEX.format(local=bundle.local_name)))

    remove_generated(github / "prompts", suffix=".prompt.md")
    written += render_skill_folders(bundle, github / "skills")

    return written
