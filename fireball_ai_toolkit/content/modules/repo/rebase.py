"""Rebase onto the remote default branch, with optional squash-first and conflict resolution."""

import subprocess
from pathlib import Path

from ..common import cli as click
from ..common.utils import success
from ..setup.properties import get_repo_local
from . import squash as squash_module

_CONFLICT_CODES = {"UU", "AA", "AU", "UA", "DD", "DU", "UD"}


def _stash_changes(repo_path: Path) -> bool:
    """Stash local changes if the working tree is dirty."""
    result = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True, check=True)
    if not result.stdout.strip():
        return False

    click.echo("Uncommitted changes detected — stashing...")
    stash_result = subprocess.run(
        ["git", "stash", "push", "--all", "-m", "auto-stash before rebase"], cwd=repo_path, check=False
    )
    if stash_result.returncode != 0:
        click.echo("Failed to stash changes.", err=True)
        raise SystemExit(1)

    click.echo("Changes stashed")
    return True


def _detect_base_branch(repo_path: Path) -> str:
    """Detect the remote default branch to rebase onto."""
    result = subprocess.run(["git", "branch", "-r"], cwd=repo_path, capture_output=True, text=True, check=True)
    branches = [line.strip() for line in result.stdout.splitlines()]
    if "origin/main" in branches:
        return "origin/main"
    if "origin/master" in branches:
        return "origin/master"
    return "origin/HEAD"


def _conflicted_files(repo_path: Path) -> list[str]:
    """Return files currently in a conflicted state."""
    result = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True, check=True)
    conflicted = []
    for line in result.stdout.splitlines():
        code = line[:2]
        if code in _CONFLICT_CODES:
            conflicted.append(line[3:].strip())
    return conflicted


def _resolve_file(repo_path: Path, file: str) -> None:
    """Interactively resolve a single conflicted file."""
    if not click.is_tty():
        return

    click.echo(f"Conflict: {file}")
    answer = input("  Resolve with [o]urs (local), [t]heirs (remote), or [s]kip (resolve manually)? [o/t/s]: ")
    answer = answer.strip().lower()

    if answer == "o":
        subprocess.run(["git", "checkout", "--ours", "--", file], cwd=repo_path, check=False)
        subprocess.run(["git", "add", "--", file], cwd=repo_path, check=False)
        click.echo(f"  {file} resolved with ours (local)")
    elif answer == "t":
        subprocess.run(["git", "checkout", "--theirs", "--", file], cwd=repo_path, check=False)
        subprocess.run(["git", "add", "--", file], cwd=repo_path, check=False)
        click.echo(f"  {file} resolved with theirs (remote)")
    else:
        click.echo(f"  {file} skipped — resolve manually, then: git add {file} && git stash drop")


def _resolve_conflicts(repo_path: Path) -> None:
    """Resolve any conflicts left over from restoring the stash."""
    conflicted = _conflicted_files(repo_path)

    if not conflicted:
        click.echo("No conflict markers detected")
        subprocess.run(["git", "stash", "drop"], cwd=repo_path, check=False)
        return

    click.echo(f"Conflicted files ({len(conflicted)}):")
    for file in conflicted:
        click.echo(f"  {file}")
    click.echo()

    for file in conflicted:
        _resolve_file(repo_path, file)

    subprocess.run(["git", "stash", "drop"], cwd=repo_path, check=False)
    click.echo()
    click.echo("Conflict resolution complete")


@click.command()
def main() -> None:
    """Rebase onto the remote default branch (optionally squash first)."""
    repo_path = get_repo_local()

    if click.is_tty() and click.confirm("Run squash before rebasing?", default=False):
        click.echo()
        squash_module.main()
        return

    click.echo()
    stashed = _stash_changes(repo_path)

    click.echo()
    click.echo("Fetching remote changes...")
    subprocess.run(["git", "fetch", "--prune"], cwd=repo_path, check=False)

    click.echo()
    base = _detect_base_branch(repo_path)
    click.echo(f"Rebasing onto {base}...")

    rebase_result = subprocess.run(["git", "rebase", base], cwd=repo_path, check=False)
    if rebase_result.returncode != 0:
        if stashed:
            click.echo("Restoring stash before exiting...")
            subprocess.run(["git", "stash", "pop"], cwd=repo_path, check=False)
        click.echo("Rebase failed. Resolve conflicts then run: git rebase --continue", err=True)
        raise SystemExit(1)

    success("Rebase complete!")
    click.echo()

    if not stashed:
        return

    click.echo("Restoring stashed changes...")
    pop_result = subprocess.run(["git", "stash", "pop"], cwd=repo_path, check=False)
    if pop_result.returncode == 0:
        click.echo("Stash restored — no conflicts")
    else:
        click.echo("Stash pop has conflicts — starting resolution...")
        click.echo()
        _resolve_conflicts(repo_path)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
