"""Render GitHub Copilot / VS Code files — all pointer stubs.

* ``.github/instructions/<slug>.instructions.md`` — ``description`` + ``applyTo`` frontmatter and a
  one-line pointer at the canonical ``.fireball_ai_toolkit/toolkit|local/instructions/<slug>.md``. Copilot's
  ``applyTo`` auto-injection then delivers the pointer; whether Copilot follows it to the real
  rules is a known tradeoff of the pointer-only model.
* ``.github/copilot-instructions.md`` — the always-on index.
* ``.github/skills/<name>/SKILL.md`` — ``name``/``description`` frontmatter only in the
  ``<name>/SKILL.md`` shape Copilot requires, body the pointer at ``.fireball_ai_toolkit/toolkit|local/skills/<name>.md``
  plus the skill's trigger phrases and its ``instructions`` / ``commands`` path lists expanded into
  a "read and follow" block.
"""

from __future__ import annotations

from pathlib import Path

from ..catalog import ContentBundle
from ._common import canonical_pointer, clean_dir, clean_subdirs, skill_stub_body, write_doc

_INDEX = """# Copilot Instructions

See `AGENTS.md` at the repo root for the project overview and the instruction-file map. The
canonical rules, commands, and skills live under `.fireball_ai_toolkit/toolkit/` (from `fireball_ai_toolkit`)
and `.fireball_ai_toolkit/{local}/` (this repo's own). Everything under `.github/instructions/*.instructions.md`
auto-applies by its `applyTo` glob and points back there. Never hand-edit a generated file.
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

    skills_dir = github / "skills"
    for skill in bundle.skills:
        written.append(
            write_doc(
                skills_dir / skill.name / "SKILL.md",
                skill_stub_body(bundle, skill, include_hints=True),
                frontmatter={"name": skill.name, "description": skill.description},
            )
        )
    clean_subdirs(skills_dir, [s.name for s in bundle.skills])

    return written
