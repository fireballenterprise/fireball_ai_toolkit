"""List topics — the active one, or the whole tree (`--all`). Backs `/topic list`."""

from __future__ import annotations

import logging

from ..common import cli as click
from . import active as topic_active
from . import update_list

LOGGER = logging.getLogger(__name__)


def _render_tree(topics: list[str], active: str | None) -> list[str]:
    """Render `/`-joined topic paths as an indented tree, starring the active leaf.

    Parent segments that are themselves registered topics are starred too; parents that only
    group children (no topic directory of their own) are shown as plain `name/` headers.
    """
    registered = set(topics)
    lines: list[str] = []
    seen: set[str] = set()
    for path in sorted(topics):
        segments = path.split("/")
        for depth, segment in enumerate(segments):
            branch = "/".join(segments[: depth + 1])
            if branch in seen:
                continue
            seen.add(branch)
            indent = "  " * depth
            is_leaf = depth == len(segments) - 1
            label = segment if (is_leaf or branch in registered) else f"{segment}/"
            marker = " ⭐" if branch == active else ""
            lines.append(f"{indent}{label}{marker}")
    return lines


@click.command()
@click.option("--all", "show_all", is_flag=True, default=False, help="Show every topic instead of just the active one")
def main(show_all: bool = False) -> None:
    """Show the active topic, or the whole topic tree when `show_all` is set."""
    active = topic_active.get_active_topic()
    topics = update_list.list_topics()

    if not show_all:
        if active is None:
            click.echo("No active topic. Run `/topic switch <path>` or `/topic list all` to see every topic.")
            return
        click.echo(f"⭐ Active Topic: {active}")
        return

    if not topics:
        click.echo("No topics yet. Run `/topic new <path>` to create one.")
        return

    click.echo("📚 Topics")
    for line in _render_tree(topics, active):
        click.echo(line)
    click.echo(f"\n{len(topics)} topic(s)" + (f" — active: {active}" if active else ""))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
