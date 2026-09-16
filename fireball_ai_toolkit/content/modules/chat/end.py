"""Close out the active chat in a topic. Backs `/chat end`."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from ..common import cli as click
from ..common.utils import error, success
from ..setup.properties import get_repo_root
from ..topic import active as topic_active
from . import active as chat_active

LOGGER = logging.getLogger(__name__)

_LOG_ENTRY_PATTERN = re.compile(r"\*\*\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] (User|Assistant):\*\*")
_OVERVIEW_PLACEHOLDER_MARKER = "_Summarize what this chat accomplished"


def auto_close(topic_dir: Path) -> None:
    """Commit whatever the active chat currently holds and clear its active-chat tracker.

    Used internally when starting a new chat or switching topics while one is still active — a
    safety net, not the user-invoked close, so it does not validate content first.
    """
    active_chat = chat_active.get_active_chat(topic_dir)
    if active_chat is None:
        return
    repo_root = get_repo_root()
    chat_path = topic_dir / "chats" / active_chat["filename"]
    subprocess.run(["git", "add", str(chat_path)], cwd=repo_root, check=False)
    subprocess.run(["git", "commit", "-m", f"Research session: {active_chat['title']}"], cwd=repo_root, check=False)
    chat_active.clear_active_chat(topic_dir)


def _validate(content: str) -> None:
    if _OVERVIEW_PLACEHOLDER_MARKER in content:
        error("`## Overview` still has placeholder text — write a real summary before running `/chat end`.")
    if not _LOG_ENTRY_PATTERN.search(content):
        error("`## Chat Log` has no real entries yet — append the conversation before running `/chat end`.")


@click.command()
def main() -> None:
    """Validate the active chat has real content, then clear its active-chat tracker."""
    topic_path = topic_active.get_active_topic()
    if topic_path is None:
        error("No active topic.")

    topic_dir = get_repo_root() / "topics" / topic_path
    active_chat = chat_active.get_active_chat(topic_dir)
    if active_chat is None:
        error("No active chat in this topic.")

    chat_path = topic_dir / "chats" / active_chat["filename"]
    _validate(chat_path.read_text())

    chat_active.clear_active_chat(topic_dir)
    success(f"Closed chat: {chat_path}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
