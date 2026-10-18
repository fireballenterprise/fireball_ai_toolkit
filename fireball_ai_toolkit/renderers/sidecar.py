"""Render ``.sidecar/`` for Fireball Sidecar.

* ``.sidecar/skills/<snake_case_name>.md`` — one flat file per skill (``add_bug.md``, ``ship_it.md``),
  no folders and no ``SKILL.md``: Sidecar reads files directly, whereas the Claude and Copilot runtimes
  require ``<name>/SKILL.md`` folders. Frontmatter ``name`` (== file stem), ``description``,
  ``argument-hint``, explicit ``user-invocable`` / ``disable-model-invocation``, ``hints`` (trigger
  phrases, including the other spellings of the name) and ``instructions``; the body is the full skill
  text. Sidecar reads either the canonical ``.fireball_ai_toolkit/skills`` or this mirror; the VS Code
  extension and the Mac app read ``.sidecar/skills``. A bundle skill's resource files are not mirrored.
* ``.sidecar/instructions/<slug>.md`` — pointer stubs (``name`` / ``description`` / ``applyTo``).
* A previous version's ``.sidecar/commands/`` and stale ``.sidecar/skills`` files are removed.
"""

from __future__ import annotations

from pathlib import Path

from ..catalog import ContentBundle, Skill, sidecar_skill_name
from ._common import canonical_pointer, clean_dir, clean_tree, remove_generated, skill_pointer, write_doc


def _hints(skill: Skill, snake: str) -> list[str]:
    """Trigger phrases: the skill's own, plus every other spelling of its name."""
    out: list[str] = []
    for hint in (*skill.hints, skill.source_name, skill.name, skill.name.replace("-", " ")):
        if hint and hint != snake and hint not in out:
            out.append(hint)
    return out


def _skill_text(bundle: ContentBundle, skill: Skill) -> str:
    body = skill.body.strip()
    return f"{body}\n\n{skill_pointer(bundle, skill)}" if body else skill_pointer(bundle, skill)


def render(bundle: ContentBundle, repo_root: Path) -> list[Path]:
    root = repo_root / ".sidecar"
    remove_generated(root / "commands")
    skill_files: list[Path] = []
    for skill in bundle.skills:
        snake = sidecar_skill_name(skill.name)
        if any(f.stem == snake for f in skill_files):
            msg = f"two skills render to .sidecar/skills/{snake}.md — rename one of them"
            raise ValueError(msg)
        skill_files.append(
            write_doc(
                root / "skills" / f"{snake}.md",
                _skill_text(bundle, skill),
                frontmatter={
                    "name": snake,
                    "description": skill.description,
                    "argument-hint": skill.argument_hint,
                    "user-invocable": "true" if skill.user_invocable else "false",
                    "disable-model-invocation": "false" if skill.ai_invocable else "true",
                    "hints": _hints(skill, snake),
                    "instructions": list(skill.instructions),
                },
            )
        )
    clean_tree(root / "skills", skill_files)

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
    return skill_files + inst_files
