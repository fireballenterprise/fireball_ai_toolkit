"""Render Claude Code files.

* ``CLAUDE.md`` is written by :mod:`.agents`.
* ``.claude/skills/<name>/SKILL.md`` — Claude Code runs a skill as ``/<name>`` or loads it itself.
  Frontmatter ``name`` (== folder), ``description``, ``argument-hint``, ``user-invocable`` /
  ``disable-model-invocation`` (always explicit), and an ``allowed-tools`` glob derived from
  the body's ``!`...``` exec lines so the skill runs without a permission prompt. Body: the full
  skill text; a bundle's extra resource files are copied alongside.
* A previous version's generated ``.claude/commands/`` files are removed (commands are skills now).
"""

from __future__ import annotations

from pathlib import Path

from ..catalog import ContentBundle
from ._common import remove_generated, render_skill_folders


def render(bundle: ContentBundle, repo_root: Path) -> list[Path]:
    claude = repo_root / ".claude"
    remove_generated(claude / "commands")
    return render_skill_folders(bundle, claude / "skills", allowed_tools=True)
