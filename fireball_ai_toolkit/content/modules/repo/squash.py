"""Anchored squash of all commits to root, with optional force push."""

import subprocess
from pathlib import Path

from ..common import cli as click
from ..common.utils import error, success
from ..setup.properties import get_repo_local


def _find_root_commit(repo_path: Path) -> str:
    """Return the SHA of the repository's root (first) commit."""
    result = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        error("Failed to find root commit.")
    return result.stdout.splitlines()[0].strip()


def _commit_subject(repo_path: Path, sha: str) -> str:
    """Return the subject line of a commit."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s", sha], cwd=repo_path, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _commits_after_root(repo_path: Path, root_sha: str) -> list[str]:
    """Return commit subjects (oldest first) for every commit after the root."""
    result = subprocess.run(
        ["git", "log", "--format=%s", "--reverse", "HEAD", f"^{root_sha}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _build_message(commits: list[str]) -> str:
    """Build a squashed commit message from a list of commit subjects."""
    bullets = "\n".join(f"- {msg}" for msg in commits)
    return f"SQUASHED:\n\n{bullets}"


def _execute_squash(repo_path: Path, root_sha: str, message: str) -> None:
    """Reset to root commit and amend it with the squashed message."""
    click.echo("Resetting to root commit (staging all subsequent changes)...")
    reset_result = subprocess.run(["git", "reset", "--soft", root_sha], cwd=repo_path, check=False)
    if reset_result.returncode != 0:
        error("git reset --soft failed.")

    click.echo("Creating squashed commit...")
    commit_result = subprocess.run(["git", "commit", "--amend", "-m", message], cwd=repo_path, check=False)
    if commit_result.returncode != 0:
        error("git commit --amend failed.")

    success("Squash complete!")


def _force_push(repo_path: Path) -> None:
    """Force push (with lease) to the remote."""
    click.echo("Force pushing to remote...")
    result = subprocess.run(["git", "push", "--force-with-lease"], cwd=repo_path, check=False)
    if result.returncode != 0:
        error("Force push failed. Try manually: git push --force-with-lease")
    success("Force push complete!")


@click.command()
def main() -> None:
    """Anchored squash of all commits to root, with optional force push."""
    repo_path = get_repo_local()

    click.echo("Finding root commit...")
    root_sha = _find_root_commit(repo_path)
    root_msg = _commit_subject(repo_path, root_sha)
    click.echo(f"Root commit: {root_sha[:7]} — {root_msg}")
    click.echo()

    click.echo("Collecting commits to squash...")
    commits = _commits_after_root(repo_path, root_sha)

    if not commits:
        click.echo("Nothing to squash — only one commit exists.")
        return

    click.echo(f"Found {len(commits)} commit(s) after root")
    click.echo()

    message = _build_message(commits)

    click.echo("Squash commit message:")
    click.echo("──────────────────────────────────")
    for line in message.splitlines():
        click.echo(line)
    click.echo("──────────────────────────────────")
    click.echo()

    if not click.confirm("Proceed with this commit message?", default=True):
        click.echo("Squash cancelled.")
        return

    click.echo()

    if not click.confirm("Squash all commits locally? This rewrites history and cannot be undone.", default=False):
        click.echo("Squash cancelled.")
        return

    click.echo()
    _execute_squash(repo_path, root_sha, message)
    click.echo()

    if click.confirm("Force push to remote?", default=False):
        click.echo()
        _force_push(repo_path)
    else:
        click.echo("Skipping force push. Run manually when ready: git push --force-with-lease")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
