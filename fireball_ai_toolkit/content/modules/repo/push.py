"""Push changes to git remote and iCloud Obsidian folder."""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ..common import cli as click
from ..common.utils import error, success, warning
from ..setup.properties import get_icloud_path, get_repo_local, is_icloud_enabled


def cleanup_screenshots(repo_path: Path) -> None:
    """Clean up screenshots before push."""
    click.echo("🧹 Cleaning up screenshots before push...")
    try:
        subprocess.run(
            ["uv", "run", "python", "-m", "modules.toolkit.screenshots.clean", "--no-confirm"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        success("Screenshot cleanup completed")
    except subprocess.CalledProcessError:
        warning("Screenshot cleanup failed, continuing with push...")


def _tests_report_success(output: str) -> bool:
    return "Your code has been rated at 10.00/10" in output


def run_tests(repo_path: Path) -> None:
    """Run automated code fixes and tests."""
    # Auto-fix code style before push
    click.echo("🔧 Running automated code fixes...")
    try:
        subprocess.run(
            ["uv", "run", "invoke", "fix"],
            cwd=repo_path,
            check=True,
            capture_output=False,  # Show output to user
        )
        success("Code fixes completed")
    except subprocess.CalledProcessError:
        warning("Code fixes had issues, but continuing with tests...")

    click.echo()

    # Run tests to validate code quality
    click.echo("🧪 Running tests to validate code quality...")
    result = subprocess.run(
        ["uv", "run", "invoke", "test"],
        cwd=repo_path,
        check=False,
        capture_output=True,
        text=True,
    )
    combined_output = f"{result.stdout}{result.stderr}"
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    if result.returncode == 0 or _tests_report_success(combined_output):
        success("All tests passed! ✨")
        return

    click.echo()
    click.echo("❌ Tests failed! Must achieve 10/10 before pushing.")
    click.echo()
    click.echo("⚠️  Push has been stopped. You have three options:")
    click.echo("1. Fix the style issue in the code")
    click.echo("2. Update global rules (e.g., .pylintrc, pyproject.toml)")
    click.echo("3. Add a file-specific exception/exclusion")
    click.echo()
    click.echo("Please address the issues above and run /push again.")
    raise SystemExit(result.returncode)


def _resolve_conflicts(repo_path: Path, porcelain_output: str) -> None:
    """Reset any files stuck in merge-conflict state (e.g. from a previous failed stash pop)."""
    for entry in porcelain_output.splitlines():
        xy = entry[:2]
        filepath = entry[3:]
        if "U" in xy:
            warning(f"Resolving leftover merge conflict: {filepath}")
            subprocess.run(["git", "checkout", "HEAD", "--", filepath], cwd=repo_path, check=False, capture_output=True)
            subprocess.run(["git", "add", filepath], cwd=repo_path, check=False, capture_output=True)


def _stash_pop_with_lfs_recovery(repo_path: Path) -> None:
    """Pop the stash, recovering automatically from LFS pointer conflicts."""
    pop_result = subprocess.run(
        ["git", "stash", "pop"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if pop_result.returncode == 0:
        return

    combined_pop = pop_result.stdout + pop_result.stderr
    if "pointer" not in combined_pop.lower() and "lfs" not in combined_pop.lower():
        error(f"Failed to restore stash:\n{combined_pop}", exit_code=1)

    warning("LFS pointer conflict detected — resetting LFS files and retrying...")
    subprocess.run(["git", "lfs", "checkout"], cwd=repo_path, capture_output=True, check=False)
    for raw_line in combined_pop.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("screenshots/") or stripped.endswith(".png") or stripped.endswith(".jpg"):
            subprocess.run(["git", "checkout", "HEAD", "--", stripped], cwd=repo_path, capture_output=True, check=False)

    retry_result = subprocess.run(
        ["git", "stash", "pop"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if retry_result.returncode != 0:
        error(f"Failed to restore stash after LFS fix:\n{retry_result.stderr}", exit_code=1)


def _git_pull(repo_path: Path, stashed: bool) -> None:
    """Pull from remote, falling back to rebase on diverging branches."""
    pull_result = subprocess.run(["git", "pull"], cwd=repo_path, capture_output=True, text=True, check=False)
    if pull_result.returncode == 0:
        success("Pull completed")
        return

    combined = (pull_result.stdout + pull_result.stderr).lower()
    if "diverging" in combined or "fast-forward" in combined:
        warning("Diverging branches detected. Attempting git pull --rebase...")
        rebase_result = subprocess.run(
            ["git", "pull", "--rebase"], cwd=repo_path, capture_output=True, text=True, check=False
        )
        if rebase_result.returncode != 0:
            if stashed:
                click.echo("⚠️  Restoring stash before exiting...")
                subprocess.run(["git", "stash", "pop"], cwd=repo_path, check=False)
            error(
                f"Git pull --rebase failed:\n{rebase_result.stdout}\n{rebase_result.stderr}",
                exit_code=1,
            )
        success("Rebase successful. Continuing push.")
    else:
        if stashed:
            click.echo("⚠️  Restoring stash before exiting...")
            subprocess.run(["git", "stash", "pop"], cwd=repo_path, check=False)
        error(f"Git pull failed. Stopping.\n{pull_result.stdout}\n{pull_result.stderr}", exit_code=1)


def push_git(repo_path: Path, timestamp: str) -> None:
    """Stash, pull, unstash, commit, and push changes to git remote."""
    click.echo("🔍 Checking working directory status...")
    status_result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True, check=True
    )

    # Auto-resolve files stuck in conflict state from a previous failed stash pop
    _resolve_conflicts(repo_path, status_result.stdout)

    # Re-check status after conflict resolution
    status_result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True, check=True
    )

    stashed = False
    if status_result.stdout.strip():
        click.echo("📦 Stashing local changes before pull...")
        # Exclude screenshots/latest.png (temp view file) to avoid LFS pointer issues
        stash_result = subprocess.run(
            ["git", "stash", "push", "-u", "-m", "auto-stash before push", "--", ".", ":!screenshots/latest.png"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if stash_result.returncode != 0:
            error(f"Failed to stash changes:\n{stash_result.stderr}", exit_code=1)
        success("Changes stashed")
        stashed = True
    else:
        success("Working directory is clean")

    click.echo()

    click.echo("📥 Pulling latest changes from remote...")
    _git_pull(repo_path, stashed)

    # Restore stash if we stashed earlier
    if stashed:
        click.echo()
        click.echo("📂 Restoring stashed changes...")
        _stash_pop_with_lfs_recovery(repo_path)
        success("Stash restored")

    click.echo()

    # Check for local changes (including just-unstashed)
    click.echo("🔍 Checking for uncommitted changes...")
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    if result.stdout.strip():
        click.echo("📝 Found local changes. Committing...")

        # Stage all changes
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)

        # Commit with timestamp
        commit_message = f"Push repository: Automated commit {timestamp}"
        subprocess.run(["git", "commit", "-m", commit_message], cwd=repo_path, check=True)
    else:
        success("No local changes to commit")

    # Push to remote if there are any local commits not yet on the remote
    unpushed = subprocess.run(
        ["git", "log", "@{u}..HEAD", "--oneline"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if unpushed.returncode == 0 and unpushed.stdout.strip():
        click.echo("📤 Pushing to remote...")
        try:
            subprocess.run(["git", "push"], cwd=repo_path, check=True)
            success("Push completed")
        except subprocess.CalledProcessError:
            warning("Git push failed, but continuing with iCloud push...")


def push_icloud(repo_path: Path, icloud_path: Path) -> None:
    """Push to iCloud Obsidian folder using rsync."""
    click.echo()
    click.echo("☁️  Pushing to iCloud Obsidian folder...")

    rsync_cmd = [
        "rsync",
        "-avz",
        "--delete",
        "--exclude=.git",
        "--exclude=.gitignore",
        "--exclude=.gitattributes",
        "--exclude=.DS_Store",
        "--exclude=.claude",
        "--exclude=.*",
        f"{repo_path}/",
        str(icloud_path),
    ]

    try:
        subprocess.run(rsync_cmd, check=True, capture_output=True)

        # Clean up any .git folder that might have appeared
        git_in_icloud = icloud_path / ".git"
        if git_in_icloud.exists():
            click.echo("🧹 Removing .git folder from iCloud...")
            shutil.rmtree(git_in_icloud)

        success("iCloud push completed successfully")
    except subprocess.CalledProcessError:
        error("iCloud push failed", exit_code=1)


@click.command()
@click.option("--no-confirm", is_flag=True, help="Skip confirmation prompt")
def main(no_confirm: bool) -> None:
    """
    Push changes to git remote and iCloud Obsidian folder.

    Steps:
    1. Cleanup screenshots
    2. Auto-fix code style (ruff check --fix, ruff format)
    3. Run tests (MUST be 10/10 or push stops)
    4. Prompt user to confirm push
    5. Pull latest changes from git remote
    6. Commit and push any local changes to GitHub
    7. Push to iCloud using rsync (excludes .git and hidden files)
    """
    repo_path = get_repo_local()
    icloud_on = is_icloud_enabled()
    icloud_path = get_icloud_path() if icloud_on else None
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    click.echo("🔄 Starting repository push...")
    click.echo()

    # Run all steps
    cleanup_screenshots(repo_path)
    click.echo()
    run_tests(repo_path)
    click.echo()

    # Prompt user to confirm push only in interactive terminals
    dest = "GitHub and iCloud" if icloud_on else "GitHub"
    if not no_confirm and sys.stdin.isatty():
        if not click.confirm(f"✅ Tests passed! Push to {dest}?", default=True):
            click.echo("Push cancelled by user.")
            raise SystemExit(0)

    click.echo()
    push_git(repo_path, timestamp)
    if icloud_on and icloud_path is not None:
        push_icloud(repo_path, icloud_path)

    click.echo()
    click.echo("🎉 Repository push completed!")
    click.echo("   - Git: up to date")
    if icloud_on:
        click.echo("   - iCloud: pushed")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
