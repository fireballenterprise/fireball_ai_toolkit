"""Start a new dated planning chat in the active topic. Backs `/chat start`."""

from __future__ import annotations

import logging
import re
from datetime import date

from ..common import cli as click
from ..common.utils import error, success
from ..setup.properties import get_repo_root
from ..topic import active as topic_active
from . import active as chat_active
from . import end as chat_end

LOGGER = logging.getLogger(__name__)

OVERVIEW_PLACEHOLDER = "_Summarize what this chat accomplished before running `/chat end`._"
LOG_PLACEHOLDER = "_Append conversation turns here as `**[YYYY-MM-DD HH:MM] User/Assistant:**` entries._"


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return slug or "chat"


def _chat_template(title: str, topic_path: str, started: str) -> str:
    return f"""# {title}

Date: {started}
Topic: {topic_path}

## Overview

{OVERVIEW_PLACEHOLDER}

## Chat Log

{LOG_PLACEHOLDER}
"""


@click.command()
@click.option("--title", default=None, help="Chat title (prompted for interactively if omitted)")
def main(title: str | None = None) -> None:
    """Start a new dated chat titled `title` in the currently active topic."""
    topic_path = topic_active.get_active_topic()
    if topic_path is None:
        error("No active topic. Run `/topic switch <path>` first.")

    topic_dir = get_repo_root() / "topics" / topic_path
    if chat_active.get_active_chat(topic_dir) is not None:
        chat_end.auto_close(topic_dir)

    if title is None:
        title = click.prompt("Chat title")

    today = date.today()
    started = f"{today:%Y-%m-%d}"
    filename = f"{today:%Y%m%d}_{_slugify(title)}.md"
    chats_dir = topic_dir / "chats"
    chats_dir.mkdir(exist_ok=True)

    chat_path = chats_dir / filename
    chat_path.write_text(_chat_template(title, topic_path, started))

    chat_active.set_active_chat(topic_dir, filename=filename, title=title, started=started, topic=topic_path)
    success(f"Started chat: {chat_path}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
