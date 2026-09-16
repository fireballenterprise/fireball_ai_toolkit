"""Update Python version to latest stable 3.x release."""

import logging
import re
import subprocess
import sys
from pathlib import Path

from ..common import cli
from ..common.utils import error, info, success, version_tuple, warning
from ..setup.properties import get_binary_version, get_repo_local, update_binary_version

LOGGER = logging.getLogger(__name__)


def get_latest_stable_python() -> tuple[int, int, int]:
    """
    Get latest stable Python 3.x minor version from uv.

    Excludes:
    - freethreaded builds
    - Alpha/beta/rc versions

    Returns:
        Tuple of (major, minor, patch) e.g. (3, 14, 2)
    """
    result = subprocess.run(
        ["uv", "python", "list"],
        capture_output=True,
        text=True,
        check=True,
    )

    versions = []
    for line in result.stdout.splitlines():
        # Parse: "cpython-3.14.2-macos-aarch64-none"
        match = re.search(r"cpython-(\d+)\.(\d+)\.(\d+)-", line)
        if match and "freethreaded" not in line:
            version_str = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
            # Exclude alpha/beta/rc: look for 'a', 'b', 'rc' in version
            if not re.search(r"[abc]|rc", version_str):
                major, minor, patch = map(int, match.groups())
                if major == 3:
                    versions.append((major, minor, patch))

    if not versions:
        error("No stable Python 3.x versions found")

    # Get highest minor version (prefer highest patch)
    latest = max(versions, key=lambda v: (v[1], v[2]))
    return latest


def get_current_python_version(repo_path: Path) -> tuple[int, int]:
    """
    Get current Python version from pyproject.toml.

    Reads: requires-python = ">=3.13"

    Returns:
        Tuple of (major, minor) e.g. (3, 13)
    """
    pyproject_path = repo_path / "pyproject.toml"

    with open(pyproject_path, encoding="utf-8") as f:
        content = f.read()

    match = re.search(r'requires-python\s*=\s*">=(\d+)\.(\d+)"', content)
    if not match:
        error("Could not find requires-python in pyproject.toml")

    return (int(match.group(1)), int(match.group(2)))


def get_files_to_update() -> list[dict]:
    """
    Get list of files and their Python version update patterns.

    Returns:
        List of dicts with 'file' and 'patterns' keys
    """
    return [
        {
            "file": "pyproject.toml",
            "patterns": [
                r'(requires-python\s*=\s*">=)(\d+\.\d+)(")',
                r'(target-version\s*=\s*"py)(\d+)(")',
            ],
        },
        {"file": ".python-version", "patterns": [r"^(\d+\.\d+)$"]},
        {"file": ".pylintrc", "patterns": [r"(py-version=)(\d+\.\d+)"]},
        {"file": "setup.sh", "patterns": [r"(--python\s+)(\d+\.\d+)"]},
        {
            "file": ".github/actions/setup_uv/action.yml",
            "patterns": [r"(--python\s+)(\d+\.\d+)"],
        },
    ]


def update_python_version_in_file(
    file_path: Path,
    patterns: list[str],
    old_version: str,  # pylint: disable=unused-argument
    new_version: str,
) -> bool:
    """
    Update Python version in a single file.

    Args:
        file_path: Path to file
        patterns: List of regex patterns to match
        old_version: Old version string (e.g., "3.13")
        new_version: New version string (e.g., "3.14")

    Returns:
        True if file was modified, False otherwise
    """
    # Special handling for .python-version (simple version-only file)
    if file_path.name == ".python-version":
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"{new_version}\n")
        return True

    # Read file content
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Apply all patterns
    for pattern in patterns:
        compiled_pattern = re.compile(pattern)
        num_groups = compiled_pattern.groups

        # Handle pyproject.toml special cases — both fields are major.minor only (a floor/target,
        # not an exact pin), so always use new_version's floor here even when new_version itself
        # carries a full x.y.z patch (e.g. from properties.yml's exact-pin caller).
        new_floor = ".".join(new_version.split(".")[:2])
        if file_path.name == "pyproject.toml":
            if "requires-python" in pattern:
                # Pattern: (requires-python\s*=\s*">=)(\d+\.\d+)(")
                # Replace group 2 with the new floor, keep groups 1 and 3
                content = re.sub(pattern, rf"\g<1>{new_floor}\g<3>", content)
            elif "target-version" in pattern:
                # Pattern: (target-version\s*=\s*"py)(\d+)(")
                # Replace group 2 with the new floor, no dots (e.g. "314"), keep groups 1 and 3
                new_py = new_floor.replace(".", "")
                content = re.sub(pattern, rf"\g<1>{new_py}\g<3>", content)
        # Standard 2-group pattern: (prefix)(version)
        # Replace group 2 with new version, keep group 1
        elif num_groups == 2:
            content = re.sub(pattern, rf"\g<1>{new_version}", content)
        elif num_groups == 1:
            # Single group pattern - replace entire match
            content = re.sub(pattern, new_version, content, flags=re.MULTILINE)
        else:
            # Fallback for unexpected patterns
            warning(f"Unexpected pattern with {num_groups} groups: {pattern}")

    # Write if changed
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    return False


def update_all_python_references(
    repo_path: Path,
    old_version: str,
    new_version: str,
) -> int:
    """
    Update Python version in all configuration files.

    Returns:
        Number of files updated
    """
    files_config = get_files_to_update()
    updated_count = 0

    for config in files_config:
        file_path = repo_path / config["file"]

        if not file_path.exists():
            warning(f"File not found: {config['file']}")
            continue

        if update_python_version_in_file(
            file_path,
            config["patterns"],
            old_version,
            new_version,
        ):
            updated_count += 1
            cli.echo(f"   ✓ {config['file']}")

    return updated_count


def update_properties_pin(new_version: str) -> bool:
    """Rewrite properties.yml's `binary_versions.python` pin to `new_version` (full x.y.z — unlike
    the other tracked files, which only pin major.minor). This is the pin `/upgrade python` reads
    as its install target, so it needs to land here too, not just in pyproject.toml/.python-version.

    Returns:
        True if the pin was found and changed, False if already current or missing.
    """
    try:
        current = get_binary_version("python")
    except KeyError:
        warning("properties.yml is missing binary_versions.python — skipping")
        return False
    if current == new_version:
        return False
    return update_binary_version("python", current, new_version)


def get_runtime_python_version() -> str:
    """Return the current runtime Python version (major.minor.patch)."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def display_python_update_table(current_version: str, latest_version: str) -> None:
    """Display a simple before/after table for Python versions."""
    cli.echo("\n🐍 Python Version Update:")
    cli.echo("╭───────────────────┬──────────────────╮")
    cli.echo("│ Current           │ Latest           │")
    cli.echo("├───────────────────┼──────────────────┤")
    current = current_version.ljust(17)
    latest = latest_version.ljust(16)
    cli.echo(f"│ {current} │ {latest} │")
    cli.echo("╰───────────────────┴──────────────────╯")


@cli.command()
@cli.option("--dry-run", is_flag=True, help="Show updates without applying")
@cli.option("--yes", "-y", "no_confirm", is_flag=True, help="Skip confirmation")
def main(dry_run: bool, no_confirm: bool) -> None:
    """
    Update Python version to latest stable 3.x release in config files.

    IMPORTANT: This only updates config files. Run /upgrade python to actually
    install the new Python version and rebuild .venv.

    Checks for the latest stable Python 3.x release and updates all configuration files,
    including properties.yml's binary_versions.python pin — the exact version /upgrade python
    installs:
    - pyproject.toml (requires-python, target-version)
    - .python-version
    - .pylintrc
    - setup.sh
    - .github/actions/setup_uv/action.yml
    - properties.yml (binary_versions.python)

    Examples:
        /update python              # Interactive mode
        /update python --dry-run    # Preview changes
        /update python --yes        # Auto-confirm
    """
    info("Checking Python version...")

    repo_path = get_repo_local()

    # No pyproject.toml → not a Python repo (e.g. a `--repo` target that's a Kotlin app). Exit 3,
    # the "nothing to do" convention the check orchestrator tolerates.
    if not (repo_path / "pyproject.toml").exists():
        success(f"No pyproject.toml in {repo_path} — skipping Python version check")
        raise SystemExit(3)

    # Get versions
    current_major, current_minor = get_current_python_version(repo_path)
    latest_major, latest_minor, latest_patch = get_latest_stable_python()

    current_runtime = get_runtime_python_version()
    current_floor = f"{current_major}.{current_minor}"
    latest_version = f"{latest_major}.{latest_minor}.{latest_patch}"

    # Display status
    cli.echo("\n📊 Python Version Status:")
    cli.echo(f"   Current runtime: {current_runtime}")
    cli.echo(f"   Latest stable:   {latest_version}")

    # Full x.y.z comparison, not just minor — properties.yml's binary_versions.python pins an
    # exact patch (like binary_versions.cdk does), so a patch-only bump still needs applying.
    if version_tuple(current_runtime) >= (latest_major, latest_minor, latest_patch):
        cli.echo()
        success(f"Python {current_runtime} is already on the latest stable version")
        raise SystemExit(3)

    display_python_update_table(current_runtime, latest_version)

    # Show files to update
    cli.echo("\n🐍 Files that will be updated:")
    for config in get_files_to_update():
        cli.echo(f"   ✓ {config['file']}")
    cli.echo("   ✓ properties.yml (binary_versions.python)")

    if dry_run:
        cli.echo("\n🔍 Dry-run mode: No changes made")
        return

    # Confirm update
    if not no_confirm:
        cli.echo()
        if not cli.confirm(f"💡 Update Python version from {current_runtime} to {latest_version}?"):
            cli.echo("Cancelled.")
            raise SystemExit(2)

    # Apply updates
    cli.echo(f"\n✏️  Updating Python version references to {latest_version}...")
    updated_count = update_all_python_references(repo_path, current_floor, latest_version)

    if update_properties_pin(latest_version):
        updated_count += 1
        cli.echo("   ✓ properties.yml (binary_versions.python)")

    if updated_count > 0:
        success(f"Updated {updated_count} files with Python {latest_version}")
        cli.echo("\n💡 Run /upgrade python to install Python and rebuild .venv")
    else:
        warning("No files were updated")

    cli.echo()


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
