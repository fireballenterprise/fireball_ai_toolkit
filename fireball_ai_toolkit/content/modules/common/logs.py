"""Central ``logging`` configuration for every module's ``LOGGER = logging.getLogger(__name__)`` —
call ``set_logging_config()`` once from ``tasks/__init__.py`` before any task runs.
"""

import logging
import os

LOGGER = logging.getLogger(__name__)


def is_ci() -> bool:
    """Return whether this process is running in a CI runner (GitHub Actions)."""
    return os.environ.get("GITHUB_ACTIONS") == "true"


def set_logging_config() -> None:
    """Configure the root logger once, for every module's LOGGER.

    CI gets a verbose format (``[module.function] message``) for scanning Action logs; local runs
    get a terse one, since the terminal already shows which invoke task is running. INFO level
    both ways — ``LOGGER.debug()`` stays opt-in (won't show unless the level is raised).
    """
    log_format = "%(levelname)s: [%(name)s.%(funcName)s] %(message)s" if is_ci() else "%(levelname)s: %(message)s"
    logging.basicConfig(format=log_format, level=logging.INFO)
