"""``/repo cleanup`` (`/cleanup`) — three phases, in order:

1. **Branch cleanup** — if the current branch has a merged GitHub PR, switch to the default
   branch, pull, delete the branch. Anything that would block that (protected branch, dirty tree,
   no merged PR) is a warning + skip, not a hard error — later phases still run.
2. **Trash sweep** — remove regenerable caches (``__pycache__/``, ``.pytest_cache/``, …) and
   *orphaned* directories under ``modules/`` / ``tasks/`` / ``tests/`` — dirs git tracks no file
   in, the residue a module move (``modules/x`` → ``modules/toolkit/x``) leaves behind. Content
   roots like ``topics/`` and the scratch ``tmp/`` are never touched.
3. **Redundant ``.gitkeep``** — ``git rm`` tracked ``.gitkeep`` placeholders in directories that
   now hold other tracked content (anywhere below them); git already materialises the directory on
   checkout, so the placeholder is dead weight. The deletion is *staged*, not committed — cleanup
   reports it and leaves the commit to you. Placeholders holding a genuinely-empty directory open
   are left alone.

The sweep runs *after* the branch switch + pull on purpose: that's exactly when the leftovers
surface (a file tracked on the old branch/layout becomes untracked once the default branch is in).

Set ``AUTO_CONFIRM=1`` (what ``/repo cleanup all`` does) to skip the sweep / ``.gitkeep`` prompts.
The module takes no CLI flags — it calls :mod:`pull`'s command entrypoint internally, which can't
tolerate stray argv.
"""

from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
from pathlib import Path

from ..common import cli as click
from ..common.utils import info, success, warning
from ..setup.properties import get_repo_local
from . import pull as pull_module
from .pr_diff import PROTECTED_BRANCHES, current_branch, detect_base_branch

_CACHE_DIRS = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov"})
_CACHE_DIR_GLOBS = ("*.egg-info",)
_CACHE_FILES = frozenset({".DS_Store", ".coverage"})
# Never descend into these — content roots and scratch stay off-limits, and .venv/.git are huge.
_SKIP_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "topics", "tmp"})
_ORPHAN_ROOTS = ("modules", "tasks", "tests")
_GITKEEP = ".gitkeep"


def _git(args: list[str], repo_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo_path, capture_output=True, text=True, check=False)


def _pr_state(repo_path: Path, branch: str) -> str | None:
    """GitHub PR state for ``branch`` (MERGED / OPEN / CLOSED), or None if there's no PR."""
    result = subprocess.run(
        ["gh", "pr", "view", branch, "--json", "state", "-q", ".state"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


# --- phase 1: branch cleanup -----------------------------------------------------------------


def _branch_cleanup(repo_path: Path) -> None:
    branch = current_branch(repo_path)

    if branch in PROTECTED_BRANCHES:
        info(f"Already on '{branch}' — pulling latest, nothing to delete.")
        pull_module.main()
        return

    if _git(["status", "--porcelain"], repo_path).stdout.strip():
        warning(f"Uncommitted changes on '{branch}' — skipping branch cleanup (trash sweep still runs).")
        return

    click.echo(f"🔍 Checking PR status for '{branch}'...")
    state = _pr_state(repo_path, branch)
    if state != "MERGED":
        found = "no PR found" if state is None else f"PR state is {state}"
        warning(f"'{branch}' isn't merged yet ({found}) — skipping branch cleanup.")
        return
    success("PR is merged")

    base_name = detect_base_branch(repo_path, branch).removeprefix("origin/")
    click.echo(f"🔀 Switching to '{base_name}' and pulling...")
    subprocess.run(["git", "checkout", base_name], cwd=repo_path, check=True)
    pull_module.main()
    subprocess.run(["git", "branch", "-D", branch], cwd=repo_path, check=True)
    success(f"Deleted '{branch}' — now on '{base_name}'")


# --- phase 2: trash sweep -------------------------------------------------------------------


def _is_cache_dir(name: str) -> bool:
    return name in _CACHE_DIRS or any(fnmatch.fnmatch(name, glob) for glob in _CACHE_DIR_GLOBS)


def _find_caches(repo_path: Path) -> list[Path]:
    hits: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        here = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in list(dirnames):
            if _is_cache_dir(name):
                hits.append(here / name)
                dirnames.remove(name)
        hits.extend(here / f for f in filenames if f in _CACHE_FILES)
    return hits


def _has_real_files(directory: Path) -> bool:
    """True if ``directory`` holds any file that isn't cache junk (ignoring cache/skip subdirs).

    Guards the sweep against deleting a directory of *new, uncommitted* work — which also has zero
    tracked files, but isn't leftover residue.
    """
    for _root, dirnames, filenames in os.walk(directory):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not _is_cache_dir(d)]
        if any(name not in _CACHE_FILES for name in filenames):
            return True
    return False


def _scan_orphans(
    repo_path: Path, directory: Path, tracked: set[str], orphans: list[Path], suspects: list[Path]
) -> None:
    """Classify dirs under an orphan root that git tracks no file in: pure cache/empty residue →
    ``orphans`` (safe to delete); anything holding non-cache untracked files → ``suspects``
    (reported, never deleted). Cache-named dirs are left to ``_find_caches``."""
    rel = directory.relative_to(repo_path).as_posix() + "/"
    if not any(path.startswith(rel) for path in tracked):
        (suspects if _has_real_files(directory) else orphans).append(directory)
        return
    for child in sorted(directory.iterdir()):
        if child.is_dir() and child.name not in _SKIP_DIRS and not _is_cache_dir(child.name):
            _scan_orphans(repo_path, child, tracked, orphans, suspects)


def _find_orphan_dirs(repo_path: Path) -> tuple[list[Path], list[Path]]:
    """Return ``(orphans, suspects)`` under the orphan roots — see :func:`_scan_orphans`."""
    tracked = {line.strip() for line in _git(["ls-files"], repo_path).stdout.splitlines() if line.strip()}
    orphans: list[Path] = []
    suspects: list[Path] = []
    for root in _ORPHAN_ROOTS:
        root_path = repo_path / root
        if root_path.is_dir():
            _scan_orphans(repo_path, root_path, tracked, orphans, suspects)
    return orphans, suspects


def _size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB"):
        if value < 1024:
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}GB"


def _remove(path: Path) -> int:
    if not path.exists():
        return 0
    size = _size(path)
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)
    return size


def _sweep_trash(repo_path: Path) -> None:
    orphans, suspects = _find_orphan_dirs(repo_path)
    caches = [c for c in _find_caches(repo_path) if not any(c == o or o in c.parents for o in orphans)]
    targets = sorted(set(orphans) | set(caches))

    click.echo()
    if suspects:
        warning("Directories git tracks nothing in, but holding untracked files — NOT removing:")
        for path in suspects:
            click.echo(f"   {path.relative_to(repo_path).as_posix()}/  (delete by hand if it's stale)")
        click.echo()

    if not targets:
        success("No local trash to sweep")
        return

    total = sum(_size(path) for path in targets)
    click.echo(f"🧹 Local trash — {len(targets)} paths, ~{_human(total)}:")
    for path in targets:
        click.echo(f"   {path.relative_to(repo_path).as_posix()}")

    if not click.confirm("Remove these?", default=True):
        click.echo("Trash sweep skipped.")
        return

    reclaimed = sum(_remove(path) for path in targets)
    success(f"Removed {len(targets)} paths — reclaimed ~{_human(reclaimed)}")


# --- phase 3: redundant .gitkeep -----------------------------------------------------------


def _find_redundant_gitkeeps(repo_path: Path) -> list[Path]:
    """Tracked ``.gitkeep`` files whose directory already holds *other* tracked content — anywhere
    below it. Git only needs one tracked file under a path to recreate the directory on checkout,
    so once real content lands the placeholder does nothing. A ``.gitkeep`` that is the only
    tracked file in its directory is still doing its job and is left alone.
    """
    tracked = [line for line in _git(["ls-files", "-z"], repo_path).stdout.split("\0") if line]
    tracked_set = set(tracked)
    redundant: list[Path] = []
    for path in tracked:
        if path.rsplit("/", 1)[-1] != _GITKEEP:
            continue
        prefix = path[: -len(_GITKEEP)]  # "dir/sub/", or "" for a repo-root .gitkeep
        if any(other != path and other.startswith(prefix) for other in tracked_set):
            redundant.append(repo_path / path)
    return redundant


def _remove_redundant_gitkeeps(repo_path: Path) -> None:
    keeps = _find_redundant_gitkeeps(repo_path)
    click.echo()
    if not keeps:
        success("No redundant .gitkeep files")
        return

    click.echo(f"📌 Redundant .gitkeep — {len(keeps)} placeholder(s) in directories that now hold tracked content:")
    for path in keeps:
        click.echo(f"   {path.relative_to(repo_path).as_posix()}")

    if not click.confirm("git rm these?", default=True):
        click.echo(".gitkeep cleanup skipped.")
        return

    rels = [path.relative_to(repo_path).as_posix() for path in keeps]
    result = _git(["rm", "--quiet", *rels], repo_path)
    if result.returncode != 0:
        warning(f"git rm failed — left in place: {result.stderr.strip()}")
        return
    success(f"Staged removal of {len(keeps)} .gitkeep file(s) — commit to finalize")


@click.command()
def main() -> None:
    """Clean up a merged feature branch, sweep local trash, drop redundant .gitkeep files."""
    repo_path = get_repo_local()
    _branch_cleanup(repo_path)
    _sweep_trash(repo_path)
    _remove_redundant_gitkeeps(repo_path)
    click.echo()
    click.echo("🎉 Cleanup complete!")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
