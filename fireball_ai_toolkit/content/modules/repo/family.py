"""Fan a ``/repo`` verb across the ``repos:`` family (pull / push / cleanup).

``/repo <verb>`` acts on the current repo; ``/repo <verb> all`` (or ``<verb> ai`` / ``<verb>
dev_prd``) routes here and runs the verb against the family in root-to-leaf ``parent`` order.
``pull`` is done inline (switch to the verified default branch + ``--ff-only``); ``push`` and
``cleanup`` shell out to each repo's own vendored module so the target's real ``invoke test`` /
``gh`` calls run in its own checkout. ``status: retired`` repos are always skipped.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ..common import cli
from ..common.route_utils import REPO_ROOT_ENV, build_env
from ..setup.properties import FamilyRepo, find_current_repo, get_family_repos, get_repo_local

_SINGLETON_NOTE = (
    "ℹ  family run requested, but properties.yml has no repos: family map (or none are cloned) —\n"
    "   running just this repo. See .ai/toolkit/instructions/repos.md to set up a repos: map."
)


def _pkg_root(path: Path) -> str:
    """Importable prefix for a repo's vendored toolkit modules (consumer vs. template layout)."""
    return "modules.toolkit" if (path / "modules" / "toolkit" / "repo").is_dir() else "modules"


def _repo_module(path: Path, verb: str) -> str:
    """The ``python -m`` target for ``verb`` inside ``path`` (handles the pr_cleanup→cleanup rename
    in family repos that haven't synced the new toolkit yet)."""
    pkg = _pkg_root(path)
    if verb == "cleanup":
        repo_dir = path / pkg.replace(".", "/") / "repo"
        leaf = "cleanup" if (repo_dir / "cleanup.py").exists() else "pr_cleanup"
        return f"{pkg}.repo.{leaf}"
    return f"{pkg}.repo.{verb}"


def _git(args: list[str], path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=path, capture_output=True, text=True, check=False)


def _default_branch(path: Path) -> str:
    """GitHub's default branch for this clone; falls back to origin/HEAD, then ``main``.

    A local clone's ``origin/HEAD`` can go stale (still ``main`` after the remote moved to
    ``development``), so ``gh`` is the primary source and we reset ``origin/HEAD`` to match.
    """
    gh = subprocess.run(
        ["gh", "repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    branch = gh.stdout.strip()
    if branch:
        return branch
    head = _git(["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], path).stdout.strip()
    return head.removeprefix("origin/") or "main"


def _pull_one(repo: FamilyRepo) -> tuple[str, str]:
    """Bring one clone's default branch up to date. Returns ``(status, detail)``."""
    branch = _default_branch(repo.path)
    _git(["remote", "set-head", "origin", branch], repo.path)

    dirty = bool(_git(["status", "--porcelain"], repo.path).stdout.strip())
    if dirty and _git(["stash", "push", "-u", "-m", "repo pull all"], repo.path).returncode != 0:
        return "error", "could not stash a dirty tree"

    if _git(["checkout", branch], repo.path).returncode != 0:
        if dirty:
            _git(["stash", "pop"], repo.path)
        return "error", f"checkout {branch} failed"

    _git(["fetch", "--prune", "origin"], repo.path)
    before = _git(["rev-parse", "HEAD"], repo.path).stdout.strip()
    pull = _git(["pull", "--ff-only", "origin", branch], repo.path)
    after = _git(["rev-parse", "HEAD"], repo.path).stdout.strip()

    note = ""
    if dirty and _git(["stash", "pop"], repo.path).returncode != 0:
        note = " (stash pop conflicted — left in stash)"

    if pull.returncode != 0:
        tail = pull.stderr.strip().splitlines()[-1] if pull.stderr.strip() else "pull failed"
        return "error", tail + note
    if before == after:
        return "current", f"{branch} @ {after[:8]}{note}"
    return "updated", f"{before[:8]} → {after[:8]}{note}"


def _run_module(repo: FamilyRepo, verb: str) -> tuple[str, str]:
    """Run a repo's own ``push`` / ``cleanup`` module in its own checkout + venv.

    ``push`` takes a ``--no-confirm`` flag; ``cleanup`` takes no argv (it calls ``pull``'s command
    entrypoint internally) so its prompt is suppressed with ``AUTO_CONFIRM`` instead.
    """
    module = _repo_module(repo.path, verb)
    env = build_env(repo.path)
    env[REPO_ROOT_ENV] = str(repo.path)
    extra = ["--no-confirm"] if verb == "push" else []
    if verb == "cleanup":
        env["AUTO_CONFIRM"] = "1"
    completed = subprocess.run(
        ["uv", "run", "--no-sync", "python", "-m", module, *extra],
        cwd=repo.path,
        env=env,
        check=False,
    )
    return ("ok", "") if completed.returncode == 0 else ("error", f"exit {completed.returncode}")


def _dispatch_single(verb: str) -> int:
    """Singleton fallback: run the single-repo verb against the current repo."""
    path = get_repo_local()
    completed = subprocess.run(
        [sys.executable, "-m", _repo_module(path, verb)],
        cwd=path,
        env=build_env(path),
        check=False,
    )
    return completed.returncode


_STATUS_MARK = {"updated": "✓", "current": "·", "ok": "✓", "error": "✗"}


def _print_summary(label: str, results: list[tuple[str, str, str]]) -> None:
    cli.echo(f"\n─── {label} — summary ───")
    width = max(len(name) for name, _, _ in results)
    for name, status, detail in results:
        mark = _STATUS_MARK.get(status, " ")
        cli.echo(f"  {mark} {name.ljust(width)}  {status}{f'  {detail}' if detail else ''}")
    failed = [name for name, status, _ in results if status == "error"]
    if failed:
        cli.echo(f"\n{len(failed)} failed: {', '.join(failed)}")


def run_family(verb: str, *, assume_yes: bool = False, scope: str | None = None) -> int:
    """Run ``verb`` (``pull`` | ``push`` | ``cleanup``) across the family (optionally a ``scope``:
    ``ai`` or ``dev_prd``)."""
    label = f"/repo {verb} {scope or 'all'}"
    repos = get_family_repos(include_self=True, scope=scope)
    if len(repos) <= 1:
        cli.echo(_SINGLETON_NOTE)
        cli.echo()
        return _dispatch_single(verb)

    if verb in ("push", "cleanup") and not assume_yes:
        cli.echo(f"{label} — {len(repos)} repos:")
        for repo in repos:
            cli.echo(f"  • {repo.org}/{repo.name}")
        if verb == "push":
            cli.echo("\nEach runs the full /push: invoke fix + invoke test + commit + push.")
        if not cli.confirm(f"Run '{verb}' in all {len(repos)} repos?", default=False):
            cli.echo("Cancelled.")
            return 1

    results: list[tuple[str, str, str]] = []
    for repo in repos:
        name = f"{repo.org}/{repo.name}"
        cli.echo(f"\n═══ {name} ═══")
        status, detail = _pull_one(repo) if verb == "pull" else _run_module(repo, verb)
        results.append((name, status, detail))

    _print_summary(label, results)
    return 0 if all(status != "error" for _, status, _ in results) else 1


def _tags(repo: FamilyRepo) -> str:
    parts = [repo.visibility or "?", repo.default_branch or "?"]
    if repo.ai:
        parts.append("ai")
    if repo.dev_prd:
        parts.append("dev→prd")
    parts.append("PR" if repo.pull_request else "direct-push")
    if not repo.use_ci:
        parts.append("no-CI")
    if repo.status != "active":
        parts.append(repo.status.upper())
    return ", ".join(parts)


def print_self() -> int:
    """Print this repo's own ``repos:`` attributes — the ship flags especially."""
    repo = find_current_repo()
    if repo is None:
        cli.echo("This repo isn't listed in properties.yml's repos: map.")
        return 0
    ship = (
        "open a PR (assigned to you); let CI run"
        if repo.pull_request
        else "commit straight to the default branch — no PR"
    )
    test = "GitHub Actions" if repo.use_ci else "local invoke tasks / CLI (no GitHub Actions)"
    cli.echo(f"{repo.org}/{repo.name}")
    cli.echo(f"  default_branch : {repo.default_branch or '?'}")
    cli.echo(f"  visibility     : {repo.visibility or '?'}")
    cli.echo(f"  parent         : {repo.parent or 'none'}")
    cli.echo(f"  ai / dev_prd    : {repo.ai} / {repo.dev_prd}")
    cli.echo(f"  pull_request   : {repo.pull_request}  → ship: {ship}")
    cli.echo(f"  use_ci         : {repo.use_ci}  → test/build/promote/release via {test}")
    return 0


def _print_tree(parent: str | None, depth: int, by_parent: dict[str | None, list[FamilyRepo]]) -> None:
    for repo in by_parent.get(parent, []):
        marker = " ← this repo" if repo.is_self else (" [no local clone]" if not repo.exists else "")
        cli.echo(f"{'  ' * depth}{repo.org}/{repo.name}  ({_tags(repo)}){marker}")
        _print_tree(repo.name, depth + 1, by_parent)


def print_map() -> int:
    """Print the ``repos:`` family map as a ``parent`` → child tree with per-repo attributes and
    local-clone state (retired repos included, tagged)."""
    repos = get_family_repos(include_self=True, include_retired=True, include_missing=True)
    if not repos:
        cli.echo("No repos: family map in properties.yml — this repo has no related-repo family.")
        return 0

    names = {repo.name for repo in repos}
    by_parent: dict[str | None, list[FamilyRepo]] = {}
    for repo in repos:
        by_parent.setdefault(repo.parent if repo.parent in names else None, []).append(repo)

    cli.echo("Repo family — parent → stamped child (visibility, default_branch, flags)\n")
    _print_tree(None, 0, by_parent)
    return 0
