"""Rebuild topics/topics_list.yml from the topic directories on disk. Backs `/topic reindex`.

A topic directory is any directory under `topics/` that contains an `AGENTS.md` (what
`init.scaffold` writes). Nesting depth is unbounded — `workshop/welding/tig` is as valid as
`workshop`. Reindexing registers every such directory and drops index entries whose directory
is gone; `topic_meta:` for a surviving topic is left untouched.

Use it after a pull that changed the topic tree, or when `/topic switch` reports a topic
"missing from the index" (though `switch` self-heals that one path on its own).
"""

from __future__ import annotations

import logging

from ..common import cli as click
from ..common.utils import info, success
from ..setup.properties import get_repo_root
from . import update_list

LOGGER = logging.getLogger(__name__)


def discover_topics() -> list[str]:
    """Return every `/`-joined topic path under `topics/` (directory holding an `AGENTS.md`)."""
    topics_root = get_repo_root() / "topics"
    if not topics_root.is_dir():
        return []
    return sorted(
        agents.parent.relative_to(topics_root).as_posix()
        for agents in topics_root.rglob("AGENTS.md")
        if agents.is_file()
    )


@click.command()
@click.option("--dry-run", is_flag=True, default=False, help="Report what would change without writing")
def main(dry_run: bool = False) -> None:
    """Reconcile topics_list.yml with the topic directories on disk."""
    found = discover_topics()
    if not found:
        info("No topic directories found under topics/ — nothing to index.")
        return

    if dry_run:
        current = set(update_list.list_topics())
        added = sorted(set(found) - current)
        removed = sorted(current - set(found))
    else:
        added, removed = update_list.sync_topics(found)

    for path in added:
        info(f"+ {path}")
    for path in removed:
        info(f"- {path} (directory gone)")

    verb = "Would reindex" if dry_run else "Reindexed"
    if added or removed:
        success(f"{verb} {len(found)} topic(s) — {len(added)} added, {len(removed)} removed")
    else:
        success(f"{verb} {len(found)} topic(s) — already in sync")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
