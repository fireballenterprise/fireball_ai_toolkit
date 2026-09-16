"""Pull updates from git remote and iCloud Obsidian folder."""

import subprocess

from ..common import cli as click
from ..common.utils import error, success, warning
from ..setup.properties import get_icloud_path, get_repo_local, is_icloud_enabled


def _decode_output(output: bytes | None) -> str:
    """Decode subprocess output safely for display and parsing."""
    if output is None:
        return ""
    return output.decode("utf-8", errors="replace")


def _restore_stash(repo_path, *, on_failure: str) -> bool:
    """Restore stashed changes and report outcome."""
    pop_result = subprocess.run(
        ["git", "stash", "pop"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if pop_result.returncode != 0:
        click.echo(pop_result.stderr.strip())
        warning(on_failure)
        return False
    success("Stashed changes restored")
    return True


def _stash_if_needed(repo_path) -> bool:
    """Stash local changes if the working tree is dirty."""
    click.echo("🔍 Checking working directory status...")
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    if not result.stdout.strip():
        success("Working directory is clean")
        click.echo()
        return False

    click.echo("⚠️  Uncommitted changes detected — stashing...")
    stash_result = subprocess.run(
        ["git", "stash", "push", "--all", "-m", "auto-stash before pull"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if stash_result.returncode != 0:
        click.echo(stash_result.stderr.strip())
        error("Failed to stash changes.", exit_code=1)

    success("Changes stashed")
    click.echo()
    return True


def _sync_from_icloud(repo_path, icloud_path) -> None:
    """Sync topics directory from iCloud and print transferred files."""
    click.echo("☁️  Pulling changes from iCloud Obsidian folder...")
    click.echo("   (syncing: topics/ including all docs/ subdirectories)")

    rsync_topics_cmd = [
        "rsync",
        "-avz",
        "--update",
        "--exclude=.git",
        "--exclude=.DS_Store",
        f"{icloud_path}/topics/",
        str(repo_path / "topics"),
    ]

    try:
        result_topics = subprocess.run(
            rsync_topics_cmd,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr_output = _decode_output(exc.stderr)
        if stderr_output:
            click.echo(stderr_output.strip())
        warning("iCloud pull failed - path may not exist or permissions issue")
        click.echo()
        return

    rsync_stdout = _decode_output(result_topics.stdout)
    success("iCloud pull completed")

    if rsync_stdout:
        lines = rsync_stdout.split("\n")
        transferred_files = [
            line
            for line in lines
            if line
            and not line.startswith("sending")
            and not line.startswith("sent")
            and not line.startswith("total")
            and not line.startswith("building")
            and "speedup" not in line.lower()
        ]

        if transferred_files:
            click.echo()
            click.echo("Files synced from iCloud:")
            for file_line in transferred_files[:10]:
                click.echo(f"  {file_line}")
            if len(transferred_files) > 10:
                click.echo(f"  ... and {len(transferred_files) - 10} more files")

    click.echo()


def _show_icloud_changes(repo_path) -> None:
    """Show git status summary for iCloud-synced changes."""
    click.echo("📊 Checking for changes pulled from iCloud...")
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    if result.stdout.strip():
        click.echo()
        click.echo("Changes detected from iCloud:")
        click.echo(result.stdout)
        click.echo()
        warning("Review changes above. Commit when ready:")
        click.echo("  git add .")
        click.echo("  git commit -m 'Pull from iCloud: [description]'")
        return

    success("No changes from iCloud")


@click.command()
def main() -> None:
    """
    Pull updates from git remote and iCloud Obsidian folder.

     Steps:
     1. Check working directory and stash local changes if needed
     2. Pull latest changes from git remote
         - Uses rebase to handle divergent local/remote history
     3. Sync from iCloud using rsync (iCloud → local)
       - Only syncs: topics/ directory (includes all subdirectories like docs/)
       - Syncs all file types (.md, .csv, etc.) within topics/
       - Only copies files that are NEWER in iCloud (uses --update)
       - Never deletes files that exist in git but not iCloud
    4. Show what changed (git status)

    Note: Does NOT auto-commit. User reviews changes manually.
    """
    repo_path = get_repo_local()
    icloud_on = is_icloud_enabled()

    click.echo("📥 Starting pull from remote..." + (" and iCloud..." if icloud_on else ""))
    click.echo()

    stashed = _stash_if_needed(repo_path)

    # Git pull with rebase to handle diverged branches without fast-forward only failures
    click.echo("📥 Pulling latest changes from git remote...")
    try:
        subprocess.run(["git", "pull", "--rebase"], cwd=repo_path, check=True)
        success("Git pull completed")
    except subprocess.CalledProcessError:
        if stashed:
            click.echo()
            click.echo("📦 Restoring stashed changes after pull failure...")
            _restore_stash(
                repo_path,
                on_failure="Stash pop failed — your changes are still in the stash. Run: git stash pop",
            )
        error("Git pull failed. Check network or merge conflicts.", exit_code=1)

    click.echo()

    if icloud_on:
        _sync_from_icloud(repo_path, get_icloud_path())
        _show_icloud_changes(repo_path)

    if stashed:
        click.echo()
        click.echo("📦 Restoring stashed changes...")
        _restore_stash(
            repo_path,
            on_failure="Stash pop failed — your changes are still in the stash. Run: git stash pop",
        )

    click.echo()
    click.echo("🎉 Pull completed!")
    click.echo("   - Git: up to date")
    if icloud_on:
        click.echo("   - iCloud: synced to local")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
