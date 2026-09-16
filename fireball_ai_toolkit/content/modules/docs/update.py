"""Docs automation entry points — called by `tasks/ai/docs.py`. See
`.github/instructions/changelogs.instructions.md`.
"""

import logging

from ..common import cli
from .lib import change_logs as lib_change_logs

LOGGER = logging.getLogger(__name__)


@cli.command()
def main() -> None:
    """Prepend any missing docs/change_logs/<category>/<name>.md entries from properties.yml."""
    LOGGER.info("Running Change Log Update")
    lib_change_logs.check_each_log(update=True)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
