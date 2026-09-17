"""Detect a PR's base branch and print commit log + diff context vs. that base."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..common import cli as click
from ..common.utils import error
from ..setup.properties import get_repo_local

PROTECTED_BRANCHES = ("development", "develop", "main", "master")
_DIFF_CHAR_LIMIT = 20_000


def current_branch(repo_path: Path) -> str:
    """Return the current checked-out branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _remote_branches(repo_path: Path) -> list[str]:
    """Return all remote-tracking branch refs (e.g. 'origin/main')."""
    result = subprocess.run(
        ["git", "branch", "-r"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines()]


def _commits_ahead(repo_path: Path, base_ref: str) -> int:
    """Return the number of commits HEAD is ahead of base_ref."""
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{base_ref}..HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return int(result.stdout.strip())


def detect_base_branch(repo_path: Path, branch: str) -> str:
    """Detect which base branch (development/main/etc.) the current branch forked from."""
    remotes = _remote_branches(repo_path)
    candidates = [f"origin/{name}" for name in PROTECTED_BRANCHES if f"origin/{name}" in remotes and name != branch]
    if not candidates:
        error("No base branch found (looked for development, develop, main, master on origin).")

    if len(candidates) == 1:
        return candidates[0]

    # Multiple candidates exist — pick the one this branch forked from most recently
    # (fewest commits between its merge-base and HEAD).
    return min(candidates, key=lambda ref: _commits_ahead(repo_path, ref))


def _commit_log(repo_path: Path, base_ref: str) -> str:
    """Return the one-line commit log for base_ref..HEAD."""
    result = subprocess.run(
        ["git", "log", "--oneline", "--no-decorate", f"{base_ref}..HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip() or "(no commits)"


def _diff_stat(repo_path: Path, base_ref: str) -> str:
    """Return the diffstat for base_ref...HEAD."""
    result = subprocess.run(
        ["git", "diff", "--stat", f"{base_ref}...HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip() or "(no changes)"


def _diff(repo_path: Path, base_ref: str) -> str:
    """Return the full diff for base_ref...HEAD, truncated if very large."""
    result = subprocess.run(
        ["git", "diff", f"{base_ref}...HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    diff_text = result.stdout
    if len(diff_text) > _DIFF_CHAR_LIMIT:
        diff_text = diff_text[:_DIFF_CHAR_LIMIT] + "\n... (diff truncated — run `git diff` locally for the full change)"
    return diff_text.strip() or "(no changes)"


@click.command()
def main() -> None:
    """Print the current branch's commit log and diff vs. its detected base branch."""
    repo_path = get_repo_local()

    click.echo("Fetching remote refs...")
    subprocess.run(["git", "fetch", "--prune"], cwd=repo_path, check=False)

    branch = current_branch(repo_path)
    base_ref = detect_base_branch(repo_path, branch)
    base_name = base_ref.removeprefix("origin/")

    click.echo(f"Current branch: {branch}")
    click.echo(f"Base branch:    {base_name}")
    click.echo()
    click.echo(f"## Commits ({base_name}..{branch})")
    click.echo(_commit_log(repo_path, base_ref))
    click.echo()
    click.echo("## Diff Stat")
    click.echo(_diff_stat(repo_path, base_ref))
    click.echo()
    click.echo("## Diff")
    click.echo(_diff(repo_path, base_ref))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
