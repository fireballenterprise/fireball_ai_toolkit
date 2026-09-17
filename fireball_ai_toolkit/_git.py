"""Thin ``git``/``gh`` subprocess helpers shared by apply / sync / contribute."""

from __future__ import annotations

import subprocess
from pathlib import Path


def git(*args: str, cwd: Path, check: bool = True) -> str:
    """Run ``git *args`` in ``cwd`` and return stripped stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def is_git_repo(path: Path) -> bool:
    try:
        return git("rev-parse", "--is-inside-work-tree", cwd=path) == "true"
    except subprocess.CalledProcessError, FileNotFoundError:
        return False


def porcelain(path: Path, pathspec: str) -> str:
    """``git status --porcelain`` limited to ``pathspec`` (``""`` when clean or not a repo)."""
    if not is_git_repo(path):
        return ""
    return git("status", "--porcelain", "--", pathspec, cwd=path)


def dirty_tracked(path: Path, pathspec: str) -> str:
    """Porcelain status for ``pathspec`` with untracked (``??``) entries dropped.

    A never-committed ``_shared/`` is not "local edits to lose" — the guard protects the committed
    baseline, so only staged/unstaged changes to already-tracked files count.
    """
    lines = [line for line in porcelain(path, pathspec).splitlines() if not line.startswith("??")]
    return "\n".join(lines)


def tracked_diff(path: Path, pathspec: str) -> str:
    if not is_git_repo(path):
        return ""
    return git("diff", "--", pathspec, cwd=path, check=False)
