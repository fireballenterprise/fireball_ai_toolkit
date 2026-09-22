"""Sync repo: pull then push with conflict resolution.

Combines /pull and /push operations with intelligent conflict handling.
If conflicts occur during pull, attempts to resolve them before proceeding to push.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ..common import cli as click
from ..common.utils import error, success, warning
from ..setup.properties import get_repo_local


def _decode_output(output: bytes | None) -> str:
    """Decode subprocess output safely for display and parsing."""
    if output is None:
        return ""
    return output.decode("utf-8", errors="replace")


def _run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _has_conflicts(repo_path: Path) -> bool:
    """Check if there are merge conflicts in the working directory."""
    result = _run_git(["diff", "--name-only", "--diff-filter=U"], repo_path, check=False)
    return bool(result.stdout.strip())


def _get_conflict_files(repo_path: Path) -> list[str]:
    """Get list of files with merge conflicts."""
    result = _run_git(["diff", "--name-only", "--diff-filter=U"], repo_path, check=False)
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def _resolve_conflicts_auto(repo_path: Path) -> bool:
    """Attempt to auto-resolve conflicts using common strategies.

    Returns True if all conflicts were resolved, False otherwise.
    """
    conflict_files = _get_conflict_files(repo_path)
    if not conflict_files:
        return True

    click.echo(f"🔄 Attempting to resolve {len(conflict_files)} conflict(s)...")

    # Strategy 1: Try rerere (reuse recorded resolution)
    rerere_result = _run_git(["rerere"], repo_path, check=False)
    if rerere_result.returncode == 0:
        click.echo("   ✓ Reused recorded resolution (rerere)")

    # Check if rerere resolved everything
    if not _has_conflicts(repo_path):
        return True

    # Strategy 2: For specific file types, prefer incoming (theirs) or current (ours)
    for filepath in _get_conflict_files(repo_path):
        # For binary files, prefer "theirs" (incoming from remote)
        file_path = repo_path / filepath
        if file_path.exists():
            try:
                # Check if file is binary
                with open(file_path, "rb") as f:
                    chunk = f.read(1024)
                    if b"\x00" in chunk:
                        # Binary file - prefer "theirs"
                        _run_git(["checkout", "--theirs", "--", filepath], repo_path, check=False)
                        _run_git(["add", filepath], repo_path, check=False)
                        click.echo(f"   ✓ Resolved binary file (theirs): {filepath}")
                        continue
            except Exception:
                pass

        # For generated files (like lock files), prefer "theirs"
        if filepath.endswith(
            ("package-lock.json", "yarn.lock", "poetry.lock", "uv.lock", "Pipfile.lock", "Gemfile.lock")
        ):
            _run_git(["checkout", "--theirs", "--", filepath], repo_path, check=False)
            _run_git(["add", filepath], repo_path, check=False)
            click.echo(f"   ✓ Resolved lock file (theirs): {filepath}")
            continue

    # Check if all resolved
    if not _has_conflicts(repo_path):
        return True

    # Strategy 3: Interactive resolution for remaining conflicts
    remaining = _get_conflict_files(repo_path)
    if remaining:
        click.echo(f"\n⚠️  {len(remaining)} conflict(s) could not be auto-resolved:")
        for f in remaining:
            click.echo(f"   - {f}")
        return False

    return True


def _abort_merge(repo_path: Path) -> None:
    """Abort the current merge/rebase operation."""
    # Try aborting rebase first, then merge
    _run_git(["rebase", "--abort"], repo_path, check=False)
    _run_git(["merge", "--abort"], repo_path, check=False)


def _stash_if_needed(repo_path: Path) -> bool:
    """Stash local changes if the working tree is dirty."""
    click.echo("🔍 Checking working directory status...")
    result = _run_git(["status", "--porcelain"], repo_path, check=False)

    if not result.stdout.strip():
        success("Working directory is clean")
        click.echo()
        return False

    click.echo("⚠️  Uncommitted changes detected — stashing...")
    stash_result = _run_git(
        ["stash", "push", "--all", "-m", "auto-stash before sync"],
        repo_path,
        check=False,
    )
    if stash_result.returncode != 0:
        click.echo(stash_result.stderr.strip())
        error("Failed to stash changes.", exit_code=1)

    success("Changes stashed")
    click.echo()
    return True


def _restore_stash(repo_path: Path, *, on_failure: str) -> bool:
    """Restore stashed changes and report outcome."""
    pop_result = _run_git(["stash", "pop"], repo_path, check=False)
    if pop_result.returncode != 0:
        click.echo(pop_result.stderr.strip())
        warning(on_failure)
        return False
    success("Stashed changes restored")
    return True


def _pull_with_conflict_resolution(repo_path: Path, stashed: bool) -> bool:
    """Pull from remote with automatic conflict resolution.

    Returns True if pull succeeded (with or without conflicts resolved),
    False if pull failed and could not be resolved.
    """
    click.echo("📥 Pulling latest changes from git remote...")

    # First try a simple pull
    pull_result = _run_git(["pull"], repo_path, check=False)

    if pull_result.returncode == 0:
        success("Git pull completed")
        return True

    # Check if it's a conflict or diverging branches
    combined = (pull_result.stdout + pull_result.stderr).lower()

    if "diverging" in combined or "fast-forward" in combined:
        warning("Diverging branches detected. Attempting rebase...")

        # Try pull with rebase
        rebase_result = _run_git(["pull", "--rebase"], repo_path, check=False)

        if rebase_result.returncode == 0:
            success("Rebase successful")
            return True

        # Check if rebase has conflicts
        if _has_conflicts(repo_path):
            if not _resolve_conflicts_auto(repo_path):
                warning("Could not auto-resolve all conflicts")
                _abort_merge(repo_path)
                if stashed:
                    _restore_stash(
                        repo_path,
                        on_failure="Stash pop failed — your changes are still in the stash. Run: git stash pop",
                    )
                error("Pull failed due to unresolved conflicts. Manual intervention required.", exit_code=1)

            # Conflicts resolved, continue rebase
            continue_result = _run_git(["rebase", "--continue"], repo_path, check=False)
            if continue_result.returncode != 0:
                _abort_merge(repo_path)
                if stashed:
                    _restore_stash(
                        repo_path,
                        on_failure="Stash pop failed — your changes are still in the stash. Run: git stash pop",
                    )
                error("Failed to continue rebase after conflict resolution.", exit_code=1)

            success("Rebase completed after conflict resolution")
            return True

        # Rebase failed for other reasons
        _abort_merge(repo_path)
        if stashed:
            _restore_stash(
                repo_path,
                on_failure="Stash pop failed — your changes are still in the stash. Run: git stash pop",
            )
        error(f"Git pull --rebase failed:\n{rebase_result.stderr}", exit_code=1)

    # Pull failed for other reasons
    if stashed:
        _restore_stash(
            repo_path,
            on_failure="Stash pop failed — your changes are still in the stash. Run: git stash pop",
        )
    error(f"Git pull failed:\n{pull_result.stderr}", exit_code=1)
    return False


def _run_tests(repo_path: Path) -> bool:
    """Run tests to validate code quality.

    Returns True if tests pass, False otherwise.
    """
    click.echo("🔧 Running automated code fixes...")
    try:
        fix_result = subprocess.run(
            ["uv", "run", "invoke", "fix"],
            cwd=repo_path,
            check=False,
            capture_output=False,
        )
        if fix_result.returncode == 0:
            success("Code fixes completed")
        else:
            warning("Code fixes had issues, but continuing with tests...")
    except Exception as e:
        warning(f"Code fixes failed: {e}")

    click.echo()
    click.echo("🧪 Running tests to validate code quality...")
    result = subprocess.run(
        ["uv", "run", "invoke", "test"],
        cwd=repo_path,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    combined_output = f"{result.stdout}{result.stderr}"
    tests_passed = result.returncode == 0 or "Your code has been rated at 10.00/10" in combined_output

    if tests_passed:
        success("All tests passed! ✨")
        return True

    click.echo()
    click.echo("❌ Tests failed! Must achieve 10/10 before pushing.")
    return False


def _commit_and_push(repo_path: Path, timestamp: str) -> bool:
    """Commit any local changes and push to remote.

    Returns True if push succeeded, False otherwise.
    """
    click.echo("🔍 Checking for uncommitted changes...")
    result = _run_git(["status", "--porcelain"], repo_path, check=False)

    if result.stdout.strip():
        click.echo("📝 Found local changes. Committing...")

        # Stage all changes
        add_result = _run_git(["add", "."], repo_path, check=False)
        if add_result.returncode != 0:
            warning("Failed to stage changes")
            return False

        # Commit with timestamp
        commit_message = f"Sync repository: Automated commit {timestamp}"
        commit_result = _run_git(["commit", "-m", commit_message], repo_path, check=False)
        if commit_result.returncode != 0:
            warning("Failed to commit changes")
            return False

        success("Changes committed")
    else:
        success("No local changes to commit")

    # Check for unpushed commits
    unpushed = _run_git(["log", "@{u}..HEAD", "--oneline"], repo_path, check=False)
    if unpushed.returncode == 0 and unpushed.stdout.strip():
        click.echo("📤 Pushing to remote...")
        push_result = _run_git(["push"], repo_path, check=False)
        if push_result.returncode != 0:
            warning(f"Git push failed:\n{push_result.stderr}")
            return False
        success("Push completed")
    else:
        success("Nothing to push (already up to date)")

    return True


@click.command()
@click.option("--no-confirm", is_flag=True, help="Skip confirmation prompt")
@click.option("--no-tests", is_flag=True, help="Skip running tests (not recommended)")
def main(no_confirm: bool, no_tests: bool) -> None:
    """
    Sync repository: pull then push with conflict resolution.

    Steps:
    1. Stash local changes if needed
    2. Pull latest changes from git remote (with auto-conflict resolution)
       - Attempts automatic resolution for common conflict types
       - Falls back to manual resolution for complex conflicts
    3. Restore stashed changes
    4. Run code fixes and tests (unless --no-tests)
    5. Commit and push any local changes

    Conflict resolution strategies:
    - Reuses recorded resolutions (rerere)
    - Binary files: prefers incoming version (theirs)
    - Lock files: prefers incoming version (theirs)
    - Other files: requires manual resolution
    """
    repo_path = get_repo_local()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    click.echo("🔄 Starting repository sync...")
    click.echo("   (pull → resolve conflicts → tests → push)")
    click.echo()

    # Step 1: Stash if needed
    stashed = _stash_if_needed(repo_path)

    # Step 2: Pull with conflict resolution
    click.echo()
    if not _pull_with_conflict_resolution(repo_path, stashed):
        # Pull failed - error already printed
        return

    # Step 3: Restore stash
    if stashed:
        click.echo()
        click.echo("📦 Restoring stashed changes...")
        if not _restore_stash(
            repo_path,
            on_failure="Stash pop failed — your changes are still in the stash. Run: git stash pop",
        ):
            error("Failed to restore stashed changes", exit_code=1)

    # Step 4: Run tests (unless skipped)
    if not no_tests:
        click.echo()
        if not _run_tests(repo_path):
            click.echo()
            click.echo("⚠️  Sync stopped: tests failed")
            click.echo("   Fix the issues and run /sync again")
            raise SystemExit(1)
    else:
        warning("Skipping tests (--no-tests)")

    # Step 5: Commit and push
    click.echo()
    if not _commit_and_push(repo_path, timestamp):
        error("Push failed", exit_code=1)

    click.echo()
    click.echo("🎉 Repository sync completed!")
    click.echo("   - Pulled latest changes")
    click.echo("   - Resolved any conflicts")
    if not no_tests:
        click.echo("   - Tests passed")
    click.echo("   - Pushed local changes")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
