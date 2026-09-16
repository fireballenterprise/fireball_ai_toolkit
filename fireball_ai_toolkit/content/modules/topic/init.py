"""Initialize a topic's chats/, docs/, and instruction files. Backs `/topic init`."""

from __future__ import annotations

import logging
from pathlib import Path

from ..common import cli as click
from ..common.utils import error, success
from ..setup.properties import get_repo_root
from . import templates, update_list

LOGGER = logging.getLogger(__name__)


def _topic_path_from_cwd() -> str:
    topics_root = get_repo_root() / "topics"
    cwd = Path.cwd().resolve()
    try:
        relative = cwd.relative_to(topics_root)
    except ValueError:
        error("Not inside topics/ — run this from within a topic directory, or use `/topic new <path>`.")
    return relative.as_posix()


def scaffold(
    topic_dir: Path,
    topic_path: str,
    description: str | None = None,
    instructions: list[str] | None = None,
) -> None:
    """Create chats/, docs/, and instruction files for a topic; register it in topics_list.yml."""
    for subdir in ("chats", "plans", "docs"):
        (topic_dir / subdir).mkdir(parents=True, exist_ok=True)
        (topic_dir / subdir / ".gitkeep").touch()
    (topic_dir / "AGENTS.md").write_text(templates.render_agents_md(topic_path, description, instructions))
    (topic_dir / "CLAUDE.md").write_text(templates.render_claude_md())
    update_list.add_topic(topic_path, description, instructions)


def split_instructions(value: str | None) -> list[str] | None:
    return [slug.strip() for slug in value.split(",") if slug.strip()] if value else None


@click.command()
@click.option("--description", default=None, help="Short description to include in the topic's AGENTS.md")
@click.option(
    "--instructions",
    default=None,
    help="Comma-separated .github/instructions/ slugs whose rules apply to this topic",
)
def main(description: str | None = None, instructions: str | None = None) -> None:
    """Initialize topic structure (chats/, docs/, instruction files) in the current directory."""
    topic_path = _topic_path_from_cwd()
    topic_dir = get_repo_root() / "topics" / topic_path
    scaffold(topic_dir, topic_path, description, split_instructions(instructions))
    success(f"Initialized topic '{topic_path}'")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
