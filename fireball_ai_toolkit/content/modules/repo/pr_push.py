"""Push the current feature branch to origin (fix → test → commit → push), for use before opening a PR.

This is intentionally separate from `modules.toolkit.repo.push` (used by `/repo push` and `/push`), which
also syncs to iCloud and assumes pushing the primary tracked branch. This module instead targets a
feature branch that may not have upstream tracking yet, as used by `/punch-it-chewy`.
"""

import subprocess
from datetime import datetime
from pathlib import Path

from ..common import cli as click
from ..common.utils import error, success, warning
from ..setup.properties import get_repo_local


def _run_tests(repo_path: Path) -> None:
    """Run automated fixes, then tests, before pushing."""
    click.echo("🔧 Running automated code fixes...")
    subprocess.run(["uv", "run", "--no-sync", "invoke", "fix"], cwd=repo_path, check=False)
    click.echo()

    click.echo("🧪 Running tests...")
    result = subprocess.run(["uv", "run", "--no-sync", "invoke", "test"], cwd=repo_path, check=False)
    if result.returncode != 0:
        error("Tests failed! Fix all offenses before pushing.\nPush stopped. Address the issues above and run again.")
    success("Tests passed!")


def _stash_if_needed(repo_path: Path) -> bool:
    """Stash local changes before pulling, if any exist."""
    click.echo("🔍 Checking working directory status...")
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True, check=True)
    if not status.stdout.strip():
        return False

    click.echo("📦 Stashing local changes before pull...")
    stash_result = subprocess.run(
        ["git", "stash", "push", "-u", "-m", "auto-stash before push"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if stash_result.returncode != 0:
        error(f"Failed to stash changes:\n{stash_result.stderr}")
    success("Changes stashed")
    return True


def _current_branch(repo_path: Path) -> str:
    """Return the current checked-out branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _remote_branch_exists(repo_path: Path, branch: str) -> bool:
    """Check whether origin already has a ref for this branch."""
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _pull_rebase(repo_path: Path, branch: str, stashed: bool) -> None:
    """Pull latest changes from remote, rebasing local work on top."""
    click.echo()
    if not _remote_branch_exists(repo_path, branch):
        click.echo(f"📥 Branch '{branch}' doesn't exist on origin yet — skipping pull.")
        return

    click.echo("📥 Pulling latest changes from remote...")
    result = subprocess.run(
        ["git", "pull", "--rebase", "origin", branch], cwd=repo_path, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        if stashed:
            click.echo("⚠️  Restoring stash before exiting...")
            subprocess.run(["git", "stash", "pop"], cwd=repo_path, check=False)
        error(f"Git pull failed. Stopping.\n{result.stdout}\n{result.stderr}")
    success("Pull completed")


def _restore_stash(repo_path: Path) -> None:
    """Restore previously stashed changes."""
    click.echo()
    click.echo("📂 Restoring stashed changes...")
    subprocess.run(["git", "stash", "pop"], cwd=repo_path, check=False)
    success("Stash restored")


def _commit_and_push(repo_path: Path, branch: str, timestamp: str) -> None:
    """Commit any local changes with a timestamped message and push to remote."""
    click.echo()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True, check=True)
    has_changes = bool(status.stdout.strip())

    if has_changes:
        click.echo("Found local changes. Committing...")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        commit_message = f"Push feature branch: Automated commit {timestamp}"
        subprocess.run(["git", "commit", "-m", commit_message], cwd=repo_path, check=True)
    else:
        success("No local changes to commit")

    if not has_changes and _remote_branch_exists(repo_path, branch):
        return

    click.echo("Pushing to remote...")
    result = subprocess.run(["git", "push", "--set-upstream", "origin", branch], cwd=repo_path, check=False)
    if result.returncode == 0:
        success("Push completed")
    else:
        warning("Git push failed.")


@click.command()
@click.option("--confirm/--no-confirm", default=True, help="Prompt for confirmation before pushing")
def main(confirm: bool = True) -> None:
    """Push the current feature branch to origin (fix → test → commit → push --set-upstream)."""
    repo_path = get_repo_local()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    _run_tests(repo_path)
    click.echo()

    if confirm and click.is_tty() and not click.confirm("Tests passed! Push branch to GitHub?", default=True):
        click.echo("Push cancelled.")
        return

    stashed = _stash_if_needed(repo_path)
    branch = _current_branch(repo_path)
    _pull_rebase(repo_path, branch, stashed)

    if stashed:
        _restore_stash(repo_path)

    _commit_and_push(repo_path, branch, timestamp)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
