"""Properties management for AI research repository."""

import os
import re
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..common import cli
from ..common.utils import info, success


def _expand_path(value: str) -> Path:
    """Expand ~ and environment variables (e.g. $HOME) in a properties.yml path value."""
    return Path(os.path.expandvars(os.path.expanduser(value)))


#: Point every repo-root/repo-local lookup at a different checkout — a wrapper that runs a routed
#: command against another managed repo sets this before invoking the module.
REPO_ROOT_ENV = "SIDECAR_REPO_ROOT"


@lru_cache(maxsize=1)
def get_repo_root() -> Path:
    """
    Find repository root by searching upward for properties.yml.

    Works from any subdirectory within the repository.

    Returns:
        Path to repository root.

    Raises:
        FileNotFoundError: If properties.yml cannot be found.
    """
    # A wrapper targeting another checkout (see common.target_repo.delegate) sets this — honour it
    # before any file search so `get_properties()` and every `topics/` path resolve there too.
    override = os.environ.get(REPO_ROOT_ENV)
    if override:
        return Path(override).resolve()

    # Start from current file location
    current = Path(__file__).resolve()

    # Search upward from current file location
    for parent in [current.parent.parent.parent] + list(current.parents):
        props_file = parent / "properties.yml"
        if props_file.exists():
            return parent

    # Also try from current working directory
    current_cwd = Path.cwd().resolve()
    for parent in [current_cwd] + list(current_cwd.parents):
        props_file = parent / "properties.yml"
        if props_file.exists():
            return parent

    msg = "Could not find repository root (properties.yml not found)"
    raise FileNotFoundError(msg)


@lru_cache(maxsize=1)
def get_properties() -> dict[str, Any]:
    """
    Load properties.yml with singleton pattern (cached).

    Returns:
        Dictionary with all repository properties.

    Raises:
        FileNotFoundError: If properties.yml does not exist.
    """
    repo_root = get_repo_root()
    props_file = repo_root / "properties.yml"

    with props_file.open() as f:
        return yaml.safe_load(f)


def get_repo_local() -> Path:
    """Local repo path: ``$SIDECAR_REPO_ROOT`` if set (a wrapper targeting another checkout), else
    ``properties.yml`` ``repo.local``.
    """
    override = os.environ.get(REPO_ROOT_ENV)
    if override:
        return Path(override)
    return _expand_path(get_properties()["repo"]["local"])


def get_repo_remote() -> str:
    """
    Get repo remote URL.

    Returns:
        Remote repository URL.
    """
    props = get_properties()
    return props["repo"]["remote"]


#: `status:` values that keep a repo out of every family fan-out (still shown by `/repo list`).
RETIRED = "retired"
#: Directory names skipped when walking a `repos_local` org base dir (retired local-only clones).
ARCHIVE_DIRS = frozenset({"_archive", "archive", "tmp"})
#: `scope` tokens accepted by `get_family_repos` / `/repo <verb> <scope>`.
FAMILY_SCOPES = ("ai", "dev_prd")


@dataclass(frozen=True)
class FamilyRepo:
    """One repo in this vault's ``repos:`` family (``properties.yml`` ``repos:`` — the nested
    ``org > name > {attrs}`` schema, or the legacy ``org: [names]`` + ``lineage:`` one)."""

    org: str
    name: str
    path: Path
    is_self: bool
    exists: bool  # a local `.git` clone is present at `path`
    default_branch: str  # "main" | "development" | "" (unknown, legacy)
    parent: str | None  # bare name of the repo it was template-stamped from
    status: str  # "active" | "retired"
    visibility: str  # "public" | "private" | ""
    ai: bool
    use_ci: bool  # GitHub Actions run for this repo — else test/build/promote/release run locally
    pull_request: bool  # ship changes via a PR — else commit straight to the default branch
    purpose: str

    @property
    def dev_prd(self) -> bool:
        """Two-branch development→main promotion — inferred from ``default_branch``."""
        return self.default_branch == "development"


def _repo_entries(repos: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """Yield ``(org, name, attrs)`` for every repo, tolerating both schemas."""
    for org, block in repos.items():
        if org == "lineage" or not block:
            continue
        if isinstance(block, dict):
            for name, attrs in block.items():
                yield org, name, attrs if isinstance(attrs, dict) else {}
        else:
            for name in block:
                yield org, name, {}


def _resolve_parents(entries: dict[str, dict[str, Any]], legacy_lineage: dict[str, list[str]]) -> dict[str, str | None]:
    """``name -> parent bare name`` from each entry's ``parent:`` key, falling back to the legacy
    ``lineage:`` adjacency."""
    child_to_parent = {child: parent for parent, kids in legacy_lineage.items() for child in kids}
    resolved: dict[str, str | None] = {}
    for name, attrs in entries.items():
        parent = attrs.get("parent")
        if parent == "none":
            resolved[name] = None
        elif parent:
            resolved[name] = str(parent)
        else:
            resolved[name] = child_to_parent.get(name)
    return resolved


def _parent_depth(name: str, parents: dict[str, str | None]) -> int:
    depth, current, seen = 0, name, set()
    while (parent := parents.get(current)) and current not in seen:
        seen.add(current)
        current, depth = parent, depth + 1
    return depth


def get_family_repos(
    *,
    include_self: bool = False,
    include_retired: bool = False,
    include_missing: bool = False,
    scope: str | None = None,
) -> list[FamilyRepo]:
    """Resolve ``properties.yml`` ``repos:`` + ``repos_local:`` into ``FamilyRepo`` records,
    ordered root-to-leaf by ``parent`` depth (then name).

    - ``status: retired`` repos are excluded unless ``include_retired``.
    - repos with no local ``.git`` clone are excluded unless ``include_missing``.
    - ``scope="ai"`` keeps only ``ai: true``; ``scope="dev_prd"`` keeps only
      ``default_branch: development``.
    - the :func:`get_repo_local` entry is flagged ``is_self`` and dropped unless ``include_self``.

    Returns ``[]`` when there is no ``repos:`` map — the caller treats that as "singleton, no
    family".
    """
    props = get_properties()
    repos = props.get("repos") or {}
    repos_local = props.get("repos_local") or {}
    legacy_lineage = _normalize_lineage(repos.get("lineage", {}))
    self_path = get_repo_local().resolve()

    rows = list(_repo_entries(repos))
    parents = _resolve_parents({name: attrs for _org, name, attrs in rows}, legacy_lineage)

    found: list[FamilyRepo] = []
    for org, name, attrs in rows:
        status = str(attrs.get("status", "active"))
        if status == RETIRED and not include_retired:
            continue
        if scope == "ai" and not bool(attrs.get("ai", False)):
            continue
        if scope == "dev_prd" and str(attrs.get("default_branch", "")) != "development":
            continue

        base = next((value for key, value in repos_local.items() if key.lower() == org.lower()), None)
        path = (_expand_path(base) / name).resolve() if base else Path(name)
        exists = bool(base) and (path / ".git").exists()
        if not exists and not include_missing:
            continue

        found.append(
            FamilyRepo(
                org=org,
                name=name,
                path=path,
                is_self=path == self_path,
                exists=exists,
                default_branch=str(attrs.get("default_branch", "")),
                parent=parents.get(name),
                status=status,
                visibility=str(attrs.get("visibility", "")),
                ai=bool(attrs.get("ai", False)),
                use_ci=bool(attrs.get("use_ci", False)),
                pull_request=bool(attrs.get("pull_request", False)),
                purpose=str(attrs.get("purpose", "")),
            )
        )

    found.sort(key=lambda repo: (_parent_depth(repo.name, parents), repo.name))
    if not include_self:
        found = [repo for repo in found if not repo.is_self]
    return found


def find_current_repo() -> FamilyRepo | None:
    """This repo's own ``FamilyRepo`` record from the ``repos:`` map (``None`` if it isn't listed).

    Use ``.pull_request`` / ``.use_ci`` to decide how to ship a change:
    ``pull_request`` false → commit straight to the default branch, no PR; ``use_ci`` false →
    test/build/promote/release with local ``invoke`` tasks, don't wait on GitHub checks.
    """
    for repo in get_family_repos(include_self=True, include_retired=True, include_missing=True):
        if repo.is_self:
            return repo
    return None


def get_binary_version(name: str) -> str:
    """Return a pinned tool version from ``binary_versions.<name>`` (e.g. "python", "cdk") — for
    tools version-pinned outside pyproject.toml / uv. Raises ``KeyError`` if the pin isn't set.
    """
    return str(get_properties()["binary_versions"][name])


def update_binary_version(name: str, old_value: str, new_value: str) -> bool:
    """Rewrite ``binary_versions.<name>`` from ``old_value`` to ``new_value`` in place, preserving
    formatting. Returns whether ``old_value`` was found and rewritten.
    """
    properties_file = get_repo_root() / "properties.yml"
    text = properties_file.read_text()
    updated, count = re.subn(rf"({re.escape(name)}:\s*){re.escape(old_value)}\b", rf"\g<1>{new_value}", text, count=1)
    if count == 0:
        return False
    properties_file.write_text(updated)
    get_properties.cache_clear()
    return True


def get_git_author() -> str:
    """Return ``git config user.name`` (or "Unknown"), for stamping a changelog/version author
    entry rather than a hand-typed name that drifts from who's actually committing.
    """
    result = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, check=False)
    name = result.stdout.strip()
    return name if result.returncode == 0 and name else "Unknown"


def is_icloud_enabled() -> bool:
    """
    Whether iCloud-Obsidian sync is turned on for /push and /pull.

    Off by default. Missing `icloud` section or `icloud.enabled` → False.

    Returns:
        True when `icloud.enabled` is truthy in properties.yml.
    """
    props = get_properties()
    return bool(props.get("icloud", {}).get("enabled", False))


def get_icloud_path() -> Path:
    """
    Get iCloud sync path as Path object.

    Returns:
        Path to iCloud sync location.
    """
    props = get_properties()
    return _expand_path(props["icloud"]["path"])


def get_screenshots_location() -> Path:
    """
    Get screenshots directory path as Path object.

    Returns:
        Path to screenshots directory.
    """
    props = get_properties()
    return _expand_path(props["screenshots"]["location"])


def get_screenshots_latest_file() -> str:
    """
    Get latest screenshot filename.

    Returns:
        Filename for latest screenshot.
    """
    props = get_properties()
    return props["screenshots"]["latest_file"]


def get_screenshots_preserve_files() -> list[str]:
    """
    Get list of screenshot files to preserve during cleanup.

    Returns:
        List of filenames to preserve.
    """
    props = get_properties()
    return props["screenshots"]["preserve_files"]


def get_screenshots_cleanup_patterns() -> list[str]:
    """
    Get list of file patterns to clean up.

    Returns:
        List of glob patterns for cleanup.
    """
    props = get_properties()
    return props["screenshots"]["cleanup_patterns"]


# --- properties.yml bootstrap (first-run writer) -------------------------------------------
# This module is clobbered to modules/toolkit/setup/ ; the tier fragments are repo-local.
# get_repo_root() can't be used here — it searches for properties.yml, which doesn't exist yet.
# This module is clobbered to modules/toolkit/setup/ ; the tier fragments stay repo-local (they
# come from the parent repos in the lineage — template_python, template_ai_vault, …).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROPERTIES_FILE = _REPO_ROOT / "properties.yml"
_TEMPLATES_DIR = _REPO_ROOT / "modules" / "setup" / "templates" / "properties"


def _normalize_lineage(raw: Any) -> dict[str, list[str]]:
    """Flatten a `lineage` value into `parent -> [child bare names]` adjacency.

    `properties.yml` stores lineage as a nested tree — a child that is itself a parent appears as a
    single-key `{name: [grandchildren]}` mapping inside its parent's list (see repos.instructions.md).
    A tier fragment contributes the already-flat `{parent: [self]}` edge. Both collapse to the same
    flat adjacency map, which is what `_merge_repos` / `_lineage_depth` / `_render_repos_block` work
    with internally.
    """
    flat: dict[str, list[str]] = {}

    def _add(parent: str, child: str) -> None:
        flat.setdefault(parent, [])
        if child not in flat[parent]:
            flat[parent].append(child)

    def _walk(parent: str, children: Any) -> None:
        for child in children or []:
            if isinstance(child, dict):
                name, grandchildren = next(iter(child.items()))
                _add(parent, name)
                _walk(name, grandchildren)
            else:
                _add(parent, child)

    for parent, children in (raw or {}).items():
        _walk(parent, children)
    return flat


def _extract_repos_block(text: str) -> tuple[str, dict[str, Any] | None]:
    """Split a top-level `repos:` block out of raw YAML text.

    Returns (text with that block removed, its parsed value) — or (text, None) if there's no
    `repos:` block (a flow-style `repos: {}` placeholder doesn't count as one to extract). Any
    `lineage` sub-key is normalized to flat `parent -> [children]` adjacency (see `_normalize_lineage`).
    """
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.rstrip("\n") == "repos:":
            end = i + 1
            while end < len(lines) and (not lines[end].strip() or lines[end][0].isspace()):
                end += 1
            block = "".join(lines[i:end])
            remaining = "".join(lines[:i] + lines[end:])
            parsed = yaml.safe_load(block)["repos"]
            if parsed and parsed.get("lineage"):
                parsed["lineage"] = _normalize_lineage(parsed["lineage"])
            return remaining, parsed
    return text, None


def _is_nested_repos_schema(repos: dict[str, Any] | None) -> bool:
    """True when ``repos:`` uses the ``org > name > {attrs}`` schema rather than the legacy
    ``org: [names]`` + ``lineage:`` one. The tier-fragment builder only speaks the legacy schema,
    so ``backfill_missing_sections`` must leave an already-migrated ``repos:`` block untouched."""
    if not repos:
        return False
    return any(isinstance(block, dict) for org, block in repos.items() if org != "lineage")


def _merge_repos(accumulated: dict[str, Any], addition: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge one tier's repos contribution into the map accumulated from earlier tiers.

    Org lists are extended (no duplicates); `lineage` (parent -> children adjacency) is merged key
    by key, extending each parent's child list (no duplicates).
    """
    merged = {org: list(names) for org, names in accumulated.items() if org != "lineage"}
    lineage = {parent: list(children) for parent, children in accumulated.get("lineage", {}).items()}
    for org, names in addition.items():
        if org == "lineage":
            for parent, children in _normalize_lineage(names).items():
                lineage.setdefault(parent, [])
                for child in children:
                    if child not in lineage[parent]:
                        lineage[parent].append(child)
            continue
        # Org lists are matched case-insensitively (a fragment may say `LevonBecker` where the
        # family normalized to `levonbecker`) — keep whatever casing is already accumulated.
        target = next((existing for existing in merged if existing.lower() == org.lower()), org)
        merged.setdefault(target, [])
        for name in names:
            if name not in merged[target]:
                merged[target].append(name)
    if lineage:
        merged["lineage"] = lineage
    return merged


def _lineage_depth(name: str, lineage: dict[str, list[str]]) -> int:
    """Return how many lineage hops bare repo `name` is from its root (0 for a root itself)."""
    parent_of = {child: parent for parent, children in lineage.items() for child in children}
    depth = 0
    current = name
    seen: set[str] = set()
    while current in parent_of and current not in seen:
        seen.add(current)
        current = parent_of[current]
        depth += 1
    return depth


def _render_lineage_children(names: list[str], lineage: dict[str, list[str]], indent: int) -> list[str]:
    """Render one level of the lineage tree: a leaf as `- name`, a parent as `- name:` + children.

    A nested sequence under a `- name:` list item must yamllint-indent 4 past that item's own dash
    (2 for the item's own key text, +2 more for its child sequence) rather than the usual 2.
    """
    pad = " " * indent
    lines = []
    for name in sorted(names):
        children = lineage.get(name)
        if children:
            lines.append(f"{pad}- {name}:")
            lines.extend(_render_lineage_children(children, lineage, indent + 4))
        else:
            lines.append(f"{pad}- {name}")
    return lines


def _render_repos_block(repos: dict[str, Any]) -> str:
    """Render a merged repos dict back into this file's hand-formatted YAML block style.

    Each org's list is ordered root-to-leaf by lineage depth, regardless of merge order. `lineage`
    renders as a nested parent -> children tree (see repos.instructions.md).
    """
    lineage: dict[str, list[str]] = repos.get("lineage", {})
    lines = ["repos:"]
    for org, names in repos.items():
        if org == "lineage":
            continue
        ordered = sorted(names, key=lambda name: _lineage_depth(name, lineage))
        lines.append(f"  {org}:")
        lines.extend(f"    - {name}" for name in ordered)
    if lineage:
        children_names = {child for children in lineage.values() for child in children}
        roots = sorted(name for name in lineage if name not in children_names)
        lines.append("  lineage:")
        for root in roots:
            lines.append(f"    {root}:")
            lines.extend(_render_lineage_children(lineage[root], lineage, indent=6))
    return "\n".join(lines) + "\n"


def _split_top_level_blocks(text: str) -> list[tuple[str, str]]:
    """Split a fragment's remaining text (its ``repos:`` block already removed) into blank-line
    delimited top-level blocks, each labeled by the first top-level YAML key it defines.

    Keeps a block's own leading comment lines (e.g. ``# region Versions``) attached — the split
    point is blank lines, not the key line itself.
    """
    blocks: list[tuple[str, str]] = []
    for chunk in re.split(r"\n\s*\n", text.strip("\n")):
        if not chunk.strip():
            continue
        match = re.search(r"^([A-Za-z_][\w.-]*):", chunk, re.MULTILINE)
        if match:
            blocks.append((match.group(1), chunk))
    return blocks


def _replace_repos_block(text: str, new_block: str) -> str:
    """Swap the file's existing ``repos:`` block for ``new_block``, in place at the same position."""
    remaining, _ = _extract_repos_block(text)
    lines = remaining.splitlines(keepends=True)
    insert_at = 1 if lines and lines[0].rstrip("\n") == "---" else 0
    while insert_at < len(lines) and not lines[insert_at].strip():
        insert_at += 1
    return "".join(lines[:insert_at]) + new_block.rstrip("\n") + "\n\n" + "".join(lines[insert_at:])


def backfill_missing_sections() -> list[str]:
    """Add any top-level section the tier fragments define that's missing from an already-existing
    properties.yml, leaving every existing value untouched. Returns the names of the sections added
    (``repos`` counts as one, covering any new orgs/lineage entries), empty if nothing to add.
    """
    text = _PROPERTIES_FILE.read_text()
    _, existing_repos = _extract_repos_block(text)

    fragment_repos: dict[str, Any] = {}
    fragment_blocks: list[tuple[str, str]] = []
    for template_file in sorted(_TEMPLATES_DIR.glob("*.yml")):
        remaining, template_repos = _extract_repos_block(template_file.read_text())
        if template_repos:
            fragment_repos = _merge_repos(fragment_repos, template_repos)
        fragment_blocks.extend(_split_top_level_blocks(remaining))

    added: list[str] = []

    if fragment_repos and not _is_nested_repos_schema(existing_repos):
        merged_repos = _merge_repos(existing_repos or {}, fragment_repos)
        if merged_repos != (existing_repos or {}):
            text = _replace_repos_block(text, _render_repos_block(merged_repos))
            added.append("repos")

    existing_lines = text.splitlines(keepends=True)
    for key, block in fragment_blocks:
        if _has_section(existing_lines, key):
            continue
        text = text.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n"
        existing_lines = text.splitlines(keepends=True)
        added.append(key)

    if added:
        _PROPERTIES_FILE.write_text(text)
    return added


def _build_initial_content() -> str:
    """Assemble a fresh properties.yml from every tier fragment under templates/properties/*.yml.

    Each fragment's own `repos` contribution is deep-merged into the accumulated map (see module
    docstring) rather than concatenated; every other section is appended as raw text, ordered
    root-to-leaf by lineage depth regardless of filename/glob order.
    """
    repos: dict[str, Any] = {}
    fragments: list[tuple[str, str]] = []
    for template_file in sorted(_TEMPLATES_DIR.glob("*.yml")):
        remaining, template_repos = _extract_repos_block(template_file.read_text())
        if template_repos:
            repos = _merge_repos(repos, template_repos)
        if remaining.strip():
            fragments.append((template_file.stem, remaining.rstrip("\n")))

    lineage = repos.get("lineage", {})
    fragments.sort(key=lambda item: _lineage_depth(item[0], lineage))

    parts = [_render_repos_block(repos).rstrip("\n")]
    parts.extend(text for _, text in fragments)
    return "---\n\n" + "\n\n".join(parts) + "\n"


def _detect_repo_local() -> str:
    """Return this repo's absolute path, with $HOME swapped in for portability."""
    home = str(Path.home())
    repo_str = str(_REPO_ROOT)
    if repo_str.startswith(home):
        return "$HOME" + repo_str[len(home) :]
    return repo_str


def _detect_repo_remote() -> str | None:
    """Return the git origin remote as 'host/user/repo', or None if there isn't one."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None

    url = result.stdout.strip()
    url = re.sub(r"^git@([^:]+):", r"\1/", url)
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"\.git$", "", url)
    return url


def _read_scalar(lines: list[str], section: str, key: str) -> str | None:
    """Return the unquoted value of `key:` within a top-level `section:` block, or None."""
    in_section = False
    for line in lines:
        if line.rstrip("\n") == f"{section}:":
            in_section = True
            continue
        if not in_section:
            continue
        if line.strip() and not line[0].isspace():
            return None  # reached the next top-level key without finding it
        match = re.match(rf"^\s*{re.escape(key)}:\s*(.*?)\s*$", line)
        if match:
            return match.group(1).strip('"')
    return None


def _replace_scalar(lines: list[str], section: str, key: str, value: str, *, quote: bool = True) -> bool:
    """Rewrite `key: ...` to `key: value` within a top-level `section:` block, in place."""
    formatted = f'"{value}"' if quote else value
    in_section = False
    for i, line in enumerate(lines):
        if line.rstrip("\n") == f"{section}:":
            in_section = True
            continue
        if not in_section:
            continue
        if line.strip() and not line[0].isspace():
            return False  # reached the next top-level key without finding it
        match = re.match(rf"^(\s*{re.escape(key)}:\s*).*$", line)
        if match:
            lines[i] = f"{match.group(1)}{formatted}\n"
            return True
    return False


def _has_section(lines: list[str], section: str) -> bool:
    """Return whether a top-level `section:` block exists (e.g. a tier fragment that wasn't present)."""
    return any(line.rstrip("\n") == f"{section}:" for line in lines)


def _is_template_repo(repo_remote: str | None) -> bool:
    """Return whether this repo is itself a template (vs. a real repo forked from one).

    Every template repo in this family is named `template_*` (template_python, template_ai_python,
    template_ai_vault, template_shopify, ...) — checked against the git remote when available,
    falling back to the local folder name so it still works before a remote is set.
    """
    name = repo_remote.rsplit("/", 1)[-1] if repo_remote else _REPO_ROOT.name
    return name.startswith("template_")


def _sync_gitignore_tracking(repo_remote: str | None) -> None:
    """Strip properties.yml's ignore line from .gitignore for a real (non-template) repo.

    Template repos always keep properties.yml gitignored — see the module docstring. A repo
    forked from one should commit it instead, so this removes the ignore line (and its
    explanatory comment) the first time setup runs there. Idempotent: a repo that's already had
    the line removed, or never had it, is left untouched.
    """
    gitignore = _REPO_ROOT / ".gitignore"
    if not gitignore.exists() or _is_template_repo(repo_remote):
        return

    text = gitignore.read_text()
    if "/properties.yml" not in text:
        return

    kept = [
        line
        for line in text.splitlines()
        if line.strip() != "/properties.yml" and "generated by `inv setup.properties`" not in line
    ]
    collapsed: list[str] = []
    for line in kept:
        if line == "" and collapsed and collapsed[-1] == "":
            continue  # the removal above left two blank lines in a row — keep just one
        collapsed.append(line)
    gitignore.write_text("\n".join(collapsed) + "\n")
    success("properties.yml is no longer gitignored — commit it along with the rest of setup")


def _prompt_icloud_enabled(lines: list[str]) -> None:
    """Ask (interactively) whether to turn on iCloud sync for a freshly created properties.yml."""
    enabled = cli.confirm(
        "Enable iCloud sync for /push and /pull? (most people don't need this — off by default)",
        default=False,
    )
    _replace_scalar(lines, "icloud", "enabled", "true" if enabled else "false", quote=False)
    if enabled:
        info("iCloud sync enabled — edit icloud.path in properties.yml to your Obsidian vault path")


@cli.command()
def main() -> None:
    """Create properties.yml from every tier fragment. If it already exists, backfill any section a
    tier fragment defines that's missing from it, leaving every existing value untouched."""
    if _PROPERTIES_FILE.exists():
        added = backfill_missing_sections()
        if added:
            for section in added:
                success(f"properties.yml: backfilled missing section '{section}'")
        else:
            info("properties.yml already up to date — nothing to backfill")
        _sync_gitignore_tracking(_detect_repo_remote())
        return

    _PROPERTIES_FILE.write_text(_build_initial_content())
    info("Created properties.yml")

    repo_local = _detect_repo_local()
    repo_remote = _detect_repo_remote()

    lines = _PROPERTIES_FILE.read_text().splitlines(keepends=True)
    _replace_scalar(lines, "repo", "local", repo_local)
    if repo_remote:
        _replace_scalar(lines, "repo", "remote", repo_remote)
    has_screenshots = _has_section(lines, "screenshots")
    if has_screenshots:
        _replace_scalar(lines, "screenshots", "location", f"{repo_local}/screenshots")
    if _has_section(lines, "icloud"):
        _prompt_icloud_enabled(lines)
    _PROPERTIES_FILE.write_text("".join(lines))
    _sync_gitignore_tracking(repo_remote)

    success(f"properties.yml: repo.local = {repo_local}")
    if repo_remote:
        success(f"properties.yml: repo.remote = {repo_remote}")
    else:
        info("No git remote 'origin' found — repo.remote left unchanged")
    if has_screenshots:
        success(f"properties.yml: screenshots.location = {repo_local}/screenshots")


if __name__ == "__main__":
    main()
