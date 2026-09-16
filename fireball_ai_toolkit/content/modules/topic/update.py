"""Regenerate every topic's (or a subset's) instruction files. Backs `/topic update`."""

from __future__ import annotations

import logging

from ..common import cli as click
from ..common.utils import success
from ..setup.properties import get_repo_root
from . import active as topic_active
from . import templates, update_list

LOGGER = logging.getLogger(__name__)


def _topics_to_update(current_only: bool, only: str | None) -> list[str]:
    registered = update_list.list_topics()
    if only:
        wanted = [slug.strip() for slug in only.split(",") if slug.strip()]
        return [path for path in registered if path in wanted]
    if current_only:
        active = topic_active.get_active_topic()
        return [active] if active else []
    return registered


@click.command()
@click.option("--dry-run", is_flag=True, default=False, help="Preview changes without writing them")
@click.option("--current-only", is_flag=True, default=False, help="Update only the active topic")
@click.option(
    "--topic",
    default=None,
    help="Comma-separated topic path(s) to regenerate instead of every topic (or --current-only)",
)
def main(dry_run: bool = False, current_only: bool = False, topic: str | None = None) -> None:
    """Regenerate AGENTS.md/CLAUDE.md for every topic (or a subset) from templates + topic_meta.

    Regeneration replaces AGENTS.md wholesale — any prose beyond what `topic_meta` carries
    (description + applicable instruction slugs) is lost. Scope with --topic/--current-only when a
    topic still has un-captured custom content.
    """
    repo_root = get_repo_root()
    topics = _topics_to_update(current_only, topic)
    if not topics:
        click.echo("No topics to update.")
        return

    for topic_path in topics:
        if dry_run:
            click.echo(f"Would update: {topic_path}")
            continue
        topic_dir = repo_root / "topics" / topic_path
        meta = update_list.topic_meta(topic_path)
        (topic_dir / "AGENTS.md").write_text(
            templates.render_agents_md(topic_path, meta.get("description"), meta.get("instructions"), meta.get("body"))
        )
        (topic_dir / "CLAUDE.md").write_text(templates.render_claude_md())

    verb = "Would update" if dry_run else "Updated"
    success(f"{verb} {len(topics)} topic(s)")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
