"""``ai-toolkit check`` — read-only drift gate for ``invoke test`` and CI.

Two invariants, checked without writing anything:

1. Every clobbered tree/file (``.fireball_ai_toolkit/``, ``modules/fireball_ai_toolkit/``,
   ``tasks/fireball_ai_toolkit/``, ``tests/fireball_ai_toolkit/``, ``setup.sh``, ``setup.ps1``) byte-matches the packaged
   ``content/``.
2. Every generated provider file byte-matches a fresh render of ``content/ai/`` +
   ``.<repo>/``.

Raises :class:`DriftError` naming the stale paths and the command to fix them.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .catalog import (
    SKILL_DESCRIPTION_MAX,
    SKILL_NAME_MAX,
    SKILL_NAME_RE,
    _split_frontmatter,
    local_layer_name,
    packaged_ai_root,
    packaged_content_root,
    read_vendor,
    vendored_files,
    vendored_trees,
)
from .render import render_repo

_IGNORE = {"__pycache__"}


class DriftError(RuntimeError):
    """A generated or clobbered file is stale relative to the packaged ``content/``."""


_DRIFT_MSG = "Toolkit-managed files are stale:\n  - {items}\nRun `invoke ai_toolkit.sync` (or `apply`) to regenerate."


class SkillValidationError(RuntimeError):
    """A generated skill would be silently dropped by Copilot's Agent Skills runtime."""


SKILL_DIRS = (".github/skills", ".claude/skills")


def validate_skills(repo_root: Path) -> None:
    """Fail if any generated ``SKILL.md`` has a name/folder outside ``[a-z0-9-]+``, ``name != folder``,
    a name over 64 chars or a description over 1024 chars.

    Copilot's Agent Skills runtime silently ignores such skills — they just stop loading — so this
    is a hard error at render time (``apply``) and in the drift gate (``check``).
    """
    problems: list[str] = []
    for rel in SKILL_DIRS:
        root = repo_root / rel
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            folder = skill_md.parent.name
            fm, _ = _split_frontmatter(skill_md.read_text(encoding="utf-8"))
            name = str(fm.get("name", ""))
            where = f"{rel}/{folder}/SKILL.md"
            if not SKILL_NAME_RE.fullmatch(folder):
                problems.append(f"{where}: folder {folder!r} is not [a-z0-9-]+")
            if not SKILL_NAME_RE.fullmatch(name):
                problems.append(f"{where}: name {name!r} is not [a-z0-9-]+")
            if name != folder:
                problems.append(f"{where}: name {name!r} != folder {folder!r}")
            if len(name) > SKILL_NAME_MAX:
                problems.append(f"{where}: name is {len(name)} chars (max {SKILL_NAME_MAX})")
            description = str(fm.get("description", ""))
            if len(description) > SKILL_DESCRIPTION_MAX:
                problems.append(f"{where}: description is {len(description)} chars (max {SKILL_DESCRIPTION_MAX})")
    if problems:
        msg = (
            "Invalid generated skills (Copilot would silently drop them):\n  - "
            + "\n  - ".join(problems)
            + "\nRename the source skill to lowercase letters, digits and hyphens, and shorten long descriptions."
        )
        raise SkillValidationError(msg)


def _files(root: Path) -> set[Path]:
    return {
        p.relative_to(root)
        for p in root.rglob("*")
        if p.is_file() and _IGNORE.isdisjoint(p.relative_to(root).parts) and p.suffix not in (".pyc", ".pyo")
    }


def _tree_mismatches(expected: Path, actual: Path, *, label: str) -> list[str]:
    if not expected.is_dir():
        return []
    if not actual.is_dir():
        return [f"{label}/ (missing — run `invoke ai_toolkit.apply`)"]
    out: list[str] = []
    expected_files, actual_files = _files(expected), _files(actual)
    out += [f"{label}/{rel} (missing)" for rel in sorted(expected_files - actual_files)]
    out += [f"{label}/{rel} (stale, not in canonical)" for rel in sorted(actual_files - expected_files)]
    out += [
        f"{label}/{rel}"
        for rel in sorted(expected_files & actual_files)
        if (expected / rel).read_bytes() != (actual / rel).read_bytes()
    ]
    return out


def check(repo_root: Path) -> None:
    """Raise :class:`DriftError` if any clobbered or generated file is out of date."""
    repo_root = repo_root.resolve()
    content = packaged_content_root()

    stale: list[str] = []
    for key, rel in vendored_trees(repo_root).items():
        stale += _tree_mismatches(content / key, repo_root / rel, label=rel)
    for src_rel, dest_rel in vendored_files(repo_root).items():
        src, dest = content / src_rel, repo_root / dest_rel
        if src.is_file() and (not dest.is_file() or src.read_bytes() != dest.read_bytes()):
            stale.append(f"{dest_rel} ({'missing' if not dest.is_file() else 'stale'})")

    if "ai" not in read_vendor(repo_root):
        if stale:
            raise DriftError(_DRIFT_MSG.format(items="\n  - ".join(stale)))
        return

    local_name = local_layer_name(repo_root)
    with tempfile.TemporaryDirectory() as tmp:
        mirror = Path(tmp).resolve()
        local = repo_root / f".{local_name}"
        if local.is_dir():
            shutil.copytree(local, mirror / f".{local_name}")
        for produced in render_repo(mirror, canonical_root=packaged_ai_root(), local_name=local_name).written:
            rel = produced.relative_to(mirror)
            on_disk = repo_root / rel
            if not on_disk.is_file():
                stale.append(f"{rel} (missing)")
            elif on_disk.read_bytes() != produced.read_bytes():
                stale.append(str(rel))
        validate_skills(mirror)  # what a fresh render would produce

    validate_skills(repo_root)  # and what is on disk now

    if stale:
        raise DriftError(_DRIFT_MSG.format(items="\n  - ".join(stale)))
