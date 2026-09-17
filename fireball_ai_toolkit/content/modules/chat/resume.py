"""Reopen an existing chat in the active topic to continue appending to it. Backs `/chat resume`."""

from __future__ import annotations

import logging
from pathlib import Path

from ..common import cli as click
from ..common.utils import error, success
from ..setup.properties import get_repo_root
from ..topic import active as topic_active
from . import active as chat_active
from . import end as chat_end

LOGGER = logging.getLogger(__name__)


def _read_started(chat_path: Path) -> str:
    for line in chat_path.read_text().splitlines():
        if line.startswith("Date:"):
            return line.removeprefix("Date:").strip()
    return ""


@click.command()
@click.option("--pattern", default=None, help="Filename/title substring to match (omit to require a single chat)")
def main(pattern: str | None = None) -> None:
    """Reopen the chat matching `pattern` (filename/title substring) in the active topic."""
    topic_path = topic_active.get_active_topic()
    if topic_path is None:
        error("No active topic. Run `/topic switch <path>` first.")

    topic_dir = get_repo_root() / "topics" / topic_path
    chats_dir = topic_dir / "chats"
    files = sorted(p.name for p in chats_dir.glob("*.md")) if chats_dir.is_dir() else []
    if not files:
        error(f"No chats in '{topic_path}' yet.")

    matches = [f for f in files if not pattern or pattern.lower() in f.lower()]
    if not matches:
        error(f"No chat matches '{pattern}'.")
    if len(matches) > 1:
        error(f"Multiple chats match '{pattern}': {', '.join(matches)}. Be more specific.")

    filename = matches[0]
    active_chat = chat_active.get_active_chat(topic_dir)
    if active_chat is not None and active_chat["filename"] != filename:
        chat_end.auto_close(topic_dir)

    chat_path = chats_dir / filename
    chat_active.set_active_chat(
        topic_dir,
        filename=filename,
        title=filename,
        started=_read_started(chat_path),
        topic=topic_path,
        status="resumed",
    )
    success(f"Resumed chat: {chat_path}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
