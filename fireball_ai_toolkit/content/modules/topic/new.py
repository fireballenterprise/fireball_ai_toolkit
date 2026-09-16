"""Create a new topic and initialize it. Backs `/topic new`."""

from __future__ import annotations

import logging

from ..common import cli as click
from ..common.utils import error, success
from ..setup.properties import get_repo_root
from . import active as topic_active
from .init import scaffold, split_instructions

LOGGER = logging.getLogger(__name__)


@click.command()
@click.option("--path", required=True, help="Topic path, relative to topics/ (e.g. fireball_gear)")
@click.option("--description", default=None, help="Short description to include in the topic's AGENTS.md")
@click.option(
    "--instructions",
    default=None,
    help="Comma-separated .github/instructions/ slugs whose rules apply to this topic",
)
def main(path: str, description: str | None = None, instructions: str | None = None) -> None:
    """Create a new topic at topics/<path>, initialize its structure, and switch to it.

    `path` may nest to any depth (`workshop/welding/tig`); missing parent directories are
    created. An existing directory is fine as long as it isn't already a scaffolded topic.
    """
    topic_dir = get_repo_root() / "topics" / path
    if (topic_dir / "AGENTS.md").is_file():
        error(f"Topic '{path}' already exists.")
    scaffold(topic_dir, path, description, split_instructions(instructions))

    # A freshly created topic becomes the active topic — otherwise the next
    # /chat start silently lands in whatever topic was active before this one.
    topic_active.set_active_topic(path)

    success(f"Created topic '{path}'")
    click.echo(f"Full path: {topic_dir}")
    click.echo(f"Instructions: {topic_dir / 'AGENTS.md'}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
