"""Common utilities for repo automation."""

import logging
import os
import sys
from pathlib import Path
from typing import NoReturn

LOGGER = logging.getLogger(__name__)


def expand_path(value: str) -> Path:
    """Expand ~ and environment variables (e.g. $HOME) in a config path value."""
    return Path(os.path.expandvars(os.path.expanduser(value)))


def success(message: str) -> None:
    """Print success message with emoji prefix."""
    print(f"✅ {message}")


def error(message: str, exit_code: int = 1) -> NoReturn:
    """Print error message to stderr and exit."""
    print(f"❌ {message}", file=sys.stderr)
    sys.exit(exit_code)


def warning(message: str) -> None:
    """Print warning message with emoji prefix."""
    print(f"⚠️ {message}")


def failure(message: str) -> None:
    """Print a definitive "no" with the same ❌ marker `error()` uses, but without exiting — for
    a task that completed successfully and learned the answer is negative (e.g. `bedrock.
    check_access` confirming a model is genuinely, permanently unavailable), as opposed to
    `warning()`'s "worth noting, might resolve itself" tone.
    """
    print(f"❌ {message}")


def info(message: str) -> None:
    """Print info message with emoji prefix."""
    print(f"📂 {message}")


def version_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted `x.y.z`-style version string into an int tuple for ordering comparisons."""
    return tuple(int(part) for part in version.split("."))


_VERBATIM_OPEN = "<!--sidecar:verbatim-->"
_VERBATIM_CLOSE = "<!--sidecar:/verbatim-->"


def verbatim(markdown: str) -> str:
    """Fence already-formatted Markdown in Sidecar verbatim markers.

    The Sidecar chat client renders a fenced region as-is in the transcript instead of routing it
    through the model for a paraphrase; a command whose frontmatter carries `commentary: skip` also
    ends the turn with no cloud round once its block(s) are shown. The markers are HTML comments, so
    any other consumer — a plain terminal, a Markdown renderer that does not know the convention —
    just sees the formatted block. See `.ai/toolkit/instructions/ai_commands.md`.
    """
    return f"{_VERBATIM_OPEN}\n{markdown.strip()}\n{_VERBATIM_CLOSE}"
