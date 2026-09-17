"""List chats in the active topic, starring the active one. Backs `/chat list`."""

from __future__ import annotations

import logging

from ..common import cli as click
from ..common.utils import error
from ..setup.properties import get_repo_root
from ..topic import active as topic_active
from . import active as chat_active

LOGGER = logging.getLogger(__name__)


@click.command()
def main() -> None:
    """Show every chat file in the active topic, starring the currently active one."""
    topic_path = topic_active.get_active_topic()
    if topic_path is None:
        error("No active topic. Run `/topic switch <path>` first.")

    topic_dir = get_repo_root() / "topics" / topic_path
    chats_dir = topic_dir / "chats"
    active_chat = chat_active.get_active_chat(topic_dir)
    active_filename = active_chat["filename"] if active_chat else None

    files = sorted(p.name for p in chats_dir.glob("*.md")) if chats_dir.is_dir() else []
    if not files:
        click.echo(f"No chats yet in '{topic_path}'. Run `/chat start <title>` to begin one.")
        return

    for filename in files:
        marker = "⭐ " if filename == active_filename else "  "
        click.echo(f"{marker}{filename}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
