"""``ai-toolkit contribute`` — promote local edits to a toolkit-managed path back as a PR.

1. Diff every clobbered tree/file (``.fireball_ai_toolkit/``, ``modules/fireball_ai_toolkit/``, ``tasks/fireball_ai_toolkit/``,
   ``tests/fireball_ai_toolkit/``, ``setup.sh``, ``setup.ps1``) against the packaged ``content/``.
2. Refuse if anything *outside* those paths differs (never carries ``.<repo>/`` or generated
   provider files).
3. In a local ``fireball_ai_toolkit`` checkout: branch off ``development``, apply the changed
   files into ``content/``, commit, push, open a PR with ``gh``. Never a direct push to ``main``.

The toolkit checkout is resolved in order: an explicit ``toolkit_repo`` arg → the
``FIREBALL_AI_TOOLKIT_REPO`` env var → a sibling ``../fireball_ai_toolkit`` dir.
"""

from __future__ import annotations

import filecmp
import os
import subprocess
from pathlib import Path

from ._git import git, is_git_repo
from .catalog import packaged_content_root, vendored_files, vendored_trees

_PACKAGE_NAME = "fireball_ai_toolkit"
_REPO_ENV_VAR = "FIREBALL_AI_TOOLKIT_REPO"
_IGNORE_PARTS = {"__pycache__"}


class ContributeError(RuntimeError):
    """Preconditions for a contribute run were not met."""


#: Deprecated alias — use :class:`ContributeError`.
UploadError = ContributeError


def _resolve_toolkit(repo_root: Path, override: Path | None) -> Path:
    env = os.environ.get(_REPO_ENV_VAR)
    candidate = (override or (Path(env) if env else repo_root.parent / _PACKAGE_NAME)).expanduser().resolve()
    pyproject = candidate / "pyproject.toml"
    if not pyproject.is_file() or f'name = "{_PACKAGE_NAME}"' not in pyproject.read_text(encoding="utf-8"):
        raise ContributeError(
            f"No {_PACKAGE_NAME} checkout at {candidate}. Pass toolkit_repo=... "
            f"or set {_REPO_ENV_VAR}=/path/to/fireball_ai_toolkit."
        )
    return candidate


def _changed(repo_root: Path, content: Path) -> list[tuple[Path, Path]]:
    """``(repo file, content-relative path)`` pairs for every clobbered file that differs."""
    out: list[tuple[Path, Path]] = []
    for key, rel in vendored_trees(repo_root).items():
        tree = repo_root / rel
        if not tree.is_dir():
            continue
        for path in sorted(p for p in tree.rglob("*") if p.is_file()):
            sub = path.relative_to(tree)
            if not _IGNORE_PARTS.isdisjoint(sub.parts) or path.suffix in (".pyc", ".pyo"):
                continue
            reference = content / key / sub
            if not reference.is_file() or not filecmp.cmp(path, reference, shallow=False):
                out.append((path, Path(key) / sub))
    for src_rel, dest_rel in vendored_files(repo_root).items():
        path = repo_root / dest_rel
        reference = content / src_rel
        if path.is_file() and (not reference.is_file() or not filecmp.cmp(path, reference, shallow=False)):
            out.append((path, Path(src_rel)))
    return out


def contribute(repo_root: Path, *, branch: str | None = None, toolkit_repo: Path | None = None) -> str:
    """Open a PR against the toolkit with this repo's toolkit-managed edits; return the PR URL."""
    repo_root = repo_root.resolve()
    managed = (*vendored_trees(repo_root).values(), *vendored_files(repo_root).values())

    excludes = [f":(exclude){p}" for p in managed]
    outside = is_git_repo(repo_root) and git("status", "--porcelain", "--", ".", *excludes, cwd=repo_root, check=False)
    if outside:
        raise ContributeError("Uncommitted changes outside the toolkit-managed paths — commit or stash them first.")

    content = packaged_content_root()
    changed = _changed(repo_root, content)
    if not changed:
        return "Toolkit-managed paths match canonical content — nothing to contribute."

    toolkit = _resolve_toolkit(repo_root, toolkit_repo)
    if git("status", "--porcelain", cwd=toolkit, check=False):
        raise ContributeError(f"{toolkit} has uncommitted changes — clean it first.")

    branch = branch or "sync_shared_content"
    git("fetch", "origin", "development", cwd=toolkit)
    git("checkout", "-B", branch, "origin/development", cwd=toolkit)
    for path, content_rel in changed:
        target = toolkit / _PACKAGE_NAME / "content" / content_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    git("add", "--", f"{_PACKAGE_NAME}/content", cwd=toolkit)
    summary = ", ".join(str(r) for _, r in changed)
    git("commit", "-m", f"content: sync from a consuming repo ({summary})", cwd=toolkit)
    git("push", "-u", "origin", branch, cwd=toolkit)

    result = subprocess.run(
        ["gh", "pr", "create", "--base", "development", "--fill"],
        cwd=toolkit,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


#: Deprecated alias — use :func:`contribute`.
upload = contribute
