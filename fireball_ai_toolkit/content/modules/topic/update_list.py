"""Manage the git-tracked index of all topic paths in topics/topics_list.yml.

The file has two keys:

- `topics:` — the sorted list of every registered topic path. Paths are `/`-joined and may
  nest arbitrarily deep (`workshop/welding/tig`); there is no depth limit.
- `topic_meta:` — an optional map of `path -> {description, instructions}` for topics
  that carry a description or a list of applicable `.github/instructions/` slugs. Only
  topics that need it appear here; the rest have no entry. `/topic update` reads this
  to regenerate each `AGENTS.md` (see `templates.render_agents_md`).

## Legacy `topics_layout:` migration

Repos created before the flat-`topics:` index used a nested `topics_layout:` tree
(`workshop: {tig_welding: {}}`). `_load()` flattens any such tree to `topics:` on read, so a
repo that pulls the new tooling keeps working with no manual step; the next write drops
`topics_layout:` for good. `/topic reindex` reconciles the index against the directories on
disk if the flatten missed a parent that is itself a topic.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

import yaml

from ..setup.properties import get_repo_root

LOGGER = logging.getLogger(__name__)

_TOPICS_LIST_FILE = "topics_list.yml"


class _IndentedDumper(yaml.SafeDumper):
    """Indent block-sequence items under their key (PyYAML's default doesn't, yamllint wants it to)."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


def _topics_list_path() -> Path:
    return get_repo_root() / "topics" / _TOPICS_LIST_FILE


def _flatten_layout(tree: dict, prefix: str = "") -> list[str]:
    """Flatten a legacy `topics_layout:` nested tree into `/`-joined leaf paths.

    A node with a non-empty dict value is a container (its children are the topics); a node
    with an empty / falsy value is a leaf topic. Recurses to any depth.
    """
    paths: list[str] = []
    for key, child in (tree or {}).items():
        path = f"{prefix}/{key}" if prefix else str(key)
        if isinstance(child, dict) and child:
            paths.extend(_flatten_layout(child, path))
        else:
            paths.append(path)
    return paths


def _load() -> dict:
    path = _topics_list_path()
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    if "topics" not in data and "topics_layout" in data:
        migrated = sorted(_flatten_layout(data.get("topics_layout") or {}))
        LOGGER.info("Migrated legacy topics_layout: (%d topics) to flat topics: index", len(migrated))
        data = {"topics": migrated, **{k: v for k, v in data.items() if k != "topics_layout"}}
    return data


def _write(topics: Iterable[str], meta: dict[str, dict]) -> None:
    topic_list = sorted(set(topics))
    payload: dict[str, object] = {"topics": topic_list}
    pruned = {path: value for path, value in sorted(meta.items()) if value and path in topic_list}
    if pruned:
        payload["topic_meta"] = pruned
    _topics_list_path().write_text(yaml.dump(payload, Dumper=_IndentedDumper, sort_keys=False))


def list_topics() -> list[str]:
    """Return all registered topic paths, sorted."""
    return sorted(_load().get("topics", []))


def all_meta() -> dict[str, dict]:
    """Return the full `topic_meta:` map (path -> {description, instructions, body})."""
    return _load().get("topic_meta", {}) or {}


def topic_meta(topic_path: str) -> dict:
    """Return `{description, instructions}` for `topic_path`, or `{}` if it has no metadata."""
    return all_meta().get(topic_path, {}) or {}


def topic_exists(topic_path: str) -> bool:
    """Return whether `topic_path` is registered and its directory exists."""
    return topic_path in list_topics() and (get_repo_root() / "topics" / topic_path).is_dir()


def add_topic(
    topic_path: str,
    description: str | None = None,
    instructions: list[str] | None = None,
    body: str | None = None,
) -> None:
    """Register `topic_path` in topics_list.yml, keeping any existing `topic_meta` intact.

    A supplied `description`/`instructions`/`body` is stored under `topic_meta:`; passing
    none for an already-registered topic leaves its metadata untouched.
    """
    data = _load()
    topics = data.get("topics", [])
    meta = data.get("topic_meta", {}) or {}

    if topic_path not in topics:
        topics.append(topic_path)

    entry = dict(meta.get(topic_path, {}) or {})
    if description is not None:
        entry["description"] = description
    if instructions is not None:
        entry["instructions"] = list(instructions)
    if body is not None:
        entry["body"] = body
    if entry:
        meta[topic_path] = entry

    _write(topics, meta)


def sync_topics(paths: Iterable[str]) -> tuple[list[str], list[str]]:
    """Replace the `topics:` index with exactly `paths`, preserving `topic_meta` for survivors.

    Returns `(added, removed)` — the paths newly registered and the stale paths dropped
    (their `topic_meta` entries, if any, go with them). Backs `/topic reindex`.
    """
    wanted = sorted(set(paths))
    current = set(_load().get("topics", []))
    added = sorted(set(wanted) - current)
    removed = sorted(current - set(wanted))
    _write(wanted, _load().get("topic_meta", {}) or {})
    return added, removed
