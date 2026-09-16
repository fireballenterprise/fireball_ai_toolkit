"""
Check GitHub Actions `uses:` references in .github/workflows/*.yml against the latest
published major-version tag on GitHub and update the pinned refs.

Only rewrites workflow files — does not run or trigger any workflow. Local reusable-workflow
refs (`uses: ./.github/workflows/x.yml`) have no `@ref` and are skipped automatically, as are
refs not pinned to a bare major tag (commit SHAs, branch names, full semver pins).

Usage:
    uv run --no-sync python -m modules.versioning.workflows
    uv run --no-sync invoke versioning.workflows
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from ..common import cli as click
from ..common.utils import info, success
from ..setup.properties import get_repo_root

LOGGER = logging.getLogger(__name__)

_USES_RE = re.compile(r"^(\s*(?:-\s+)?uses:\s*)([\w.-]+/[\w.-]+(?:/[\w./-]+)?)@([\w.-]+)\s*(?:#.*)?$")
_MAJOR_TAG_RE = re.compile(r"^v?(\d+)$")


def _iter_workflow_files(repo_root: Path) -> list[Path]:
    """Return all workflow YAML files under .github/workflows/."""
    workflows_dir = repo_root / ".github" / "workflows"
    return sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))


def _find_uses(path: Path) -> list[dict]:
    """Find `uses: owner/repo[/path]@ref` lines in a workflow file."""
    found = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = _USES_RE.match(line)
        if match:
            found.append({"file": path, "line": lineno, "action": match.group(2), "ref": match.group(3)})
    return found


def _repo_slug(action: str) -> str:
    """Reduce an action ref path to its owner/repo (strip any subdirectory/workflow-file suffix)."""
    parts = action.split("/")
    return "/".join(parts[:2])


def _latest_major_tag(repo_slug: str) -> str | None:
    """Return the highest bare-major version tag (e.g. "v5") published for a GitHub repo, or None."""
    result = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", f"https://github.com/{repo_slug}.git"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    majors = [
        int(m.group(1))
        for tag in result.stdout.splitlines()
        if (m := _MAJOR_TAG_RE.match(tag.rsplit("/", maxsplit=1)[-1]))
    ]
    return f"v{max(majors)}" if majors else None


def _find_updates(repo_root: Path) -> list[dict]:
    """Scan every workflow file for `uses:` refs that have a newer major version tag available."""
    updates = []
    latest_by_slug: dict[str, str | None] = {}
    for path in _iter_workflow_files(repo_root):
        for use in _find_uses(path):
            major_match = _MAJOR_TAG_RE.match(use["ref"])
            if not major_match:
                continue  # not pinned to a bare major tag (SHA, branch, full semver) — skip

            slug = _repo_slug(use["action"])
            if slug not in latest_by_slug:
                latest_by_slug[slug] = _latest_major_tag(slug)
            latest = latest_by_slug[slug]
            if latest is None or int(latest[1:]) <= int(major_match.group(1)):
                continue

            updates.append(
                {
                    "file": use["file"],
                    "line": use["line"],
                    "action": use["action"],
                    "current": use["ref"],
                    "latest": latest,
                }
            )
    return updates


def _display_updates_table(repo_root: Path, updates: list[dict]) -> None:
    """Print a File:Line | Action | Current | Latest table."""
    locations = [f"{u['file'].relative_to(repo_root)}:{u['line']}" for u in updates]
    loc_width = max(len("File:Line"), *(len(loc) for loc in locations))
    action_width = max(len("Action"), *(len(u["action"]) for u in updates))
    current_width = max(len("Current"), *(len(u["current"]) for u in updates))
    latest_width = max(len("Latest"), *(len(u["latest"]) for u in updates))

    def border(left: str, mid: str, right: str) -> str:
        widths = (loc_width, action_width, current_width, latest_width)
        return left + mid.join("─" * (w + 2) for w in widths) + right

    click.echo(border("╭", "┬", "╮"))
    click.echo(
        f"│ {'File:Line'.ljust(loc_width)} │ {'Action'.ljust(action_width)} │ "
        f"{'Current'.ljust(current_width)} │ {'Latest'.ljust(latest_width)} │"
    )
    click.echo(border("├", "┼", "┤"))
    for update, loc in zip(updates, locations, strict=True):
        click.echo(
            f"│ {loc.ljust(loc_width)} │ {update['action'].ljust(action_width)} │ "
            f"{update['current'].ljust(current_width)} │ {update['latest'].ljust(latest_width)} │"
        )
    click.echo(border("╰", "┴", "╯"))


def _apply_updates(updates: list[dict]) -> None:
    """Rewrite each `action@ref` occurrence in place, one file at a time."""
    by_file: dict[Path, list[dict]] = {}
    for update in updates:
        by_file.setdefault(update["file"], []).append(update)

    for path, file_updates in by_file.items():
        text = path.read_text(encoding="utf-8")
        for update in file_updates:
            text = text.replace(f"{update['action']}@{update['current']}", f"{update['action']}@{update['latest']}")
        path.write_text(text, encoding="utf-8")


@click.command()
@click.option("--dry-run", is_flag=True, help="Show available updates without writing changes")
@click.option("--yes", "-y", "no_confirm", is_flag=True, help="Skip the confirmation prompt")
def main(dry_run: bool = False, no_confirm: bool = False) -> None:
    """Check GitHub Actions `uses:` refs against the latest major version tags and update them."""
    info("Checking .github/workflows/ action versions...")
    repo_root = get_repo_root()
    updates = _find_updates(repo_root)

    if not updates:
        success("All workflow action references are already at their latest major version.")
        return

    click.echo(f"\n{len(updates)} action reference(s) have a newer major version available:\n")
    _display_updates_table(repo_root, updates)

    if dry_run:
        click.echo("\nDry run: no changes made.")
        return

    if not no_confirm and not click.confirm(f"\nUpdate {len(updates)} action reference(s)?"):
        click.echo("Cancelled.")
        return

    _apply_updates(updates)
    success(f"Updated {len(updates)} action reference(s) in .github/workflows/")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
