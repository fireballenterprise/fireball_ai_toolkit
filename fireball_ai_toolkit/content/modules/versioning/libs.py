"""Update Python package dependencies in pyproject.toml to latest versions.

IMPORTANT: This only updates the config file. Run /upgrade libs to actually
install the new versions.
"""

import json
import logging
import re
import subprocess
from pathlib import Path

import tomlkit

from ..common import cli
from ..common.utils import error, info, success
from ..setup.properties import get_repo_local

LOGGER = logging.getLogger(__name__)


def get_outdated_packages() -> list[dict]:
    """Get list of outdated packages from uv pip list."""
    result = subprocess.run(
        ["uv", "pip", "list", "--outdated", "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        error(f"Failed to get outdated packages: {result.stderr}")

    return json.loads(result.stdout) if result.stdout else []


def get_installed_packages() -> list[dict]:
    """Get list of installed packages from uv pip list."""
    result = subprocess.run(
        ["uv", "pip", "list", "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        error(f"Failed to get installed packages: {result.stderr}")

    return json.loads(result.stdout) if result.stdout else []


def load_pyproject(repo_path: Path):
    """Load pyproject.toml with tomlkit to preserve formatting."""
    pyproject_path = repo_path / "pyproject.toml"

    if not pyproject_path.exists():
        error(f"pyproject.toml not found at {pyproject_path}")

    with open(pyproject_path, encoding="utf-8") as f:
        return tomlkit.load(f), pyproject_path


def parse_dependency(dep_string: str) -> dict | None:
    """Parse dependency string into name, operator, version components.

    Examples:
        "click~=8.1.7" -> {"name": "click", "operator": "~=", "version": "8.1.7"}
        "pytest==8.3.4" -> {"name": "pytest", "operator": "==", "version": "8.3.4"}
    """
    match = re.match(r"^([a-zA-Z0-9_-]+)\s*([~=><]+)\s*([\d.]+)", dep_string)
    if not match:
        return None

    return {
        "name": match.group(1),
        "operator": match.group(2),
        "version": match.group(3),
    }


def get_declared_dependency_names(toml_doc) -> set[str]:
    """Return lowercase names of every dependency declared in [project.dependencies] and
    [project.optional-dependencies]."""
    names: set[str] = set()

    if "project" in toml_doc and "dependencies" in toml_doc["project"]:
        for dep_string in toml_doc["project"]["dependencies"]:
            parsed = parse_dependency(dep_string)
            if parsed:
                names.add(parsed["name"].lower())

    if "project" in toml_doc and "optional-dependencies" in toml_doc["project"]:
        for deps_list in toml_doc["project"]["optional-dependencies"].values():
            for dep_string in deps_list:
                parsed = parse_dependency(dep_string)
                if parsed:
                    names.add(parsed["name"].lower())

    return names


def find_updates(toml_doc, outdated_packages: list[dict], installed_packages: list[dict]) -> list[dict]:
    """Find dependencies needing updates in both dependencies and optional-dependencies.

    Returns:
        List of update dictionaries with:
            - package: package name
            - old: old version with operator (e.g., "~=8.1.7")
            - new: new version with operator (e.g., "~=8.3.1")
            - group: dependency group name
            - index: index in the list
            - list_ref: reference to the list in tomlkit document
    """
    updates = []

    # Create lowercase lookup for outdated and installed packages
    outdated_lookup = {pkg["name"].lower(): pkg for pkg in outdated_packages}
    installed_lookup = {pkg["name"].lower(): pkg for pkg in installed_packages}

    def resolve_latest(pkg_lower: str) -> str | None:
        if pkg_lower in outdated_lookup:
            return outdated_lookup[pkg_lower]["latest_version"]
        if pkg_lower in installed_lookup:
            return installed_lookup[pkg_lower]["version"]
        return None

    # Process [project.dependencies]
    if "project" in toml_doc and "dependencies" in toml_doc["project"]:
        deps_list = toml_doc["project"]["dependencies"]
        for i, dep_string in enumerate(deps_list):
            parsed = parse_dependency(dep_string)
            if not parsed:
                continue

            # Case-insensitive lowercase matching
            pkg_lower = parsed["name"].lower()
            latest_version = resolve_latest(pkg_lower)
            if latest_version and parsed["version"] != latest_version:
                updates.append(
                    {
                        "package": parsed["name"],
                        "old": f"{parsed['operator']}{parsed['version']}",
                        "new": f"{parsed['operator']}{latest_version}",
                        "specified_version": parsed["version"],
                        "latest_version": latest_version,
                        "group": "dependencies",
                        "index": i,
                        "list_ref": deps_list,
                    }
                )

    # Process [project.optional-dependencies]
    if "project" in toml_doc and "optional-dependencies" in toml_doc["project"]:
        for group_name, deps_list in toml_doc["project"]["optional-dependencies"].items():
            for i, dep_string in enumerate(deps_list):
                parsed = parse_dependency(dep_string)
                if not parsed:
                    continue

                pkg_lower = parsed["name"].lower()
                latest_version = resolve_latest(pkg_lower)
                if latest_version and parsed["version"] != latest_version:
                    updates.append(
                        {
                            "package": parsed["name"],
                            "old": f"{parsed['operator']}{parsed['version']}",
                            "new": f"{parsed['operator']}{latest_version}",
                            "specified_version": parsed["version"],
                            "latest_version": latest_version,
                            "group": group_name,
                            "index": i,
                            "list_ref": deps_list,
                        }
                    )

    return updates


def display_updates_table(updates: list[dict]) -> None:
    """Display updates grouped by dependency section with ASCII table."""
    if not updates:
        return

    # Group updates by section
    grouped = {}
    for update in updates:
        group = update["group"]
        if group not in grouped:
            grouped[group] = []
        grouped[group].append(update)

    # Display each group
    for group, group_updates in grouped.items():
        if group == "dependencies":
            cli.echo("\n[project.dependencies]")
        else:
            cli.echo(f"\n[project.optional-dependencies.{group}]")

        pkg_width = max(len("Package"), *(len(u["package"]) for u in group_updates))
        current_width = max(len("Current"), *(len(u.get("specified_version", "")) for u in group_updates))
        latest_width = max(len("Latest"), *(len(u.get("latest_version", "")) for u in group_updates))

        def border(left: str, mid: str, right: str, widths: tuple[int, int, int]) -> str:
            pkg, current, latest = widths
            return f"{left}{'─' * (pkg + 2)}{mid}{'─' * (current + 2)}{mid}{'─' * (latest + 2)}{right}"

        widths = (pkg_width, current_width, latest_width)

        # Table header
        cli.echo(border("╭", "┬", "╮", widths))
        cli.echo(
            f"│ {'Package'.ljust(pkg_width)} │ {'Current'.ljust(current_width)} │ {'Latest'.ljust(latest_width)} │"
        )
        cli.echo(border("├", "┼", "┤", widths))

        # Table rows
        for update in group_updates:
            pkg = update["package"].ljust(pkg_width)
            old = update.get("specified_version", "").ljust(current_width)
            new = update.get("latest_version", "").ljust(latest_width)
            cli.echo(f"│ {pkg} │ {old} │ {new} │")

        # Table footer
        cli.echo(border("╰", "┴", "╯", widths))


def apply_updates(updates: list[dict]) -> None:
    """Apply updates to the tomlkit document in-place, preserving operators."""
    for update in updates:
        parsed = parse_dependency(str(update["list_ref"][update["index"]]))
        if not parsed:
            continue

        # Extract new version from the "new" field (e.g., "~=8.3.1" -> "8.3.1")
        new_version = update["new"].split(parsed["operator"])[1]
        new_dep_string = f"{parsed['name']}{parsed['operator']}{new_version}"

        # Update in place (tomlkit preserves structure)
        update["list_ref"][update["index"]] = new_dep_string


def save_pyproject(toml_doc, pyproject_path: Path) -> None:
    """Save updated pyproject.toml preserving all formatting."""
    with open(pyproject_path, "w", encoding="utf-8") as f:
        tomlkit.dump(toml_doc, f)


@cli.command()
@cli.option("--dry-run", is_flag=True, help="Show updates without applying")
@cli.option("--yes", "-y", "no_confirm", is_flag=True, help="Skip confirmation")
def main(dry_run: bool, no_confirm: bool) -> None:
    """
    Update Python package dependencies in pyproject.toml to latest versions.

    IMPORTANT: This only updates the config file. Run /upgrade libs to actually
    install the new versions.

    Checks for outdated packages and updates both [project.dependencies]
    and [project.optional-dependencies] sections, preserving version
    constraint operators (~=, ==, >=, etc.).

    Examples:
        /update libs              # Interactive mode
        /update libs --dry-run    # Preview changes
        /update libs --yes        # Auto-confirm
    """
    info("Checking for dependency updates...")

    # Get repository path
    repo_path = get_repo_local()

    # No pyproject.toml → not a Python repo (e.g. a `--repo` target that's a Kotlin app). Exit 3,
    # the "nothing to do" convention the check orchestrator tolerates.
    if not (repo_path / "pyproject.toml").exists():
        success(f"No pyproject.toml in {repo_path} — skipping dependency check")
        raise SystemExit(3)

    # Get installed and outdated packages
    installed_packages = get_installed_packages()
    outdated_packages = get_outdated_packages()

    # Load pyproject.toml
    toml_doc, pyproject_path = load_pyproject(repo_path)

    # Find updates
    updates = find_updates(toml_doc, outdated_packages, installed_packages)

    if not updates:
        success("All pyproject.toml dependencies are up to date!")
        if outdated_packages:
            cli.echo(f"   (Found {len(outdated_packages)} outdated packages not in pyproject.toml)")
        raise SystemExit(3)

    # Display updates
    cli.echo(f"\n📦 Found {len(updates)} outdated dependencies in pyproject.toml:")
    display_updates_table(updates)

    # Dry run mode
    if dry_run:
        cli.echo("\n🔍 Dry-run mode: No changes made")
        return

    # Confirmation
    if not no_confirm:
        cli.echo()
        if not cli.confirm(f"💡 Update all {len(updates)} dependencies to latest versions?"):
            cli.echo("Cancelled.")
            raise SystemExit(2)

    # Apply updates
    cli.echo(f"\n✏️  Updating {len(updates)} dependencies in pyproject.toml...")
    apply_updates(updates)
    save_pyproject(toml_doc, pyproject_path)
    success(f"Updated {len(updates)} dependencies in pyproject.toml")
    cli.echo("\n💡 Run /upgrade libs to install these updates")
    cli.echo()


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
