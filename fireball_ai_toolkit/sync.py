"""``ai-toolkit sync`` — the smart wrapper ``/toolkit_sync`` and the skill call.

The AI does the asking; this module only reports state and runs the primitive the caller chooses:

1. :func:`inspect` — is any toolkit-managed path modified vs the last commit? Returns the diff so
   the caller can ask "contribute these first, or discard?".
2. :func:`run` — once resolved: ``apply(force=True)`` (re-clobber every managed path + regenerate).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ._git import dirty_tracked, tracked_diff
from .apply import apply
from .catalog import vendored_files, vendored_trees
from .render import RenderResult


def _managed(repo_root: Path) -> tuple[str, ...]:
    """The toolkit-managed repo paths this repo actually vendors (``.ai-toolkit.yml``)."""
    return (*vendored_trees(repo_root).values(), *vendored_files(repo_root).values())


@dataclass(frozen=True)
class SyncPlan:
    dirty: bool
    shared_diff: str
    message: str


def inspect(repo_root: Path) -> SyncPlan:
    """Report whether any toolkit-managed path has uncommitted edits, without changing anything."""
    repo_root = repo_root.resolve()
    managed = _managed(repo_root)
    status = "\n".join(s for p in managed if (s := dirty_tracked(repo_root, p)))
    if not status:
        return SyncPlan(
            dirty=False,
            shared_diff="",
            message="Toolkit-managed paths are clean — safe to `invoke ai_toolkit.apply`.",
        )
    diff = "\n".join(d for p in managed if (d := tracked_diff(repo_root, p)))
    return SyncPlan(
        dirty=True,
        shared_diff=diff,
        message=(
            f"Toolkit-managed paths have uncommitted edits:\n{status}\n\n"
            "Contribute them to the toolkit first (`invoke ai_toolkit.contribute`) or discard "
            "them, then apply."
        ),
    )


def run(repo_root: Path, *, force: bool = False) -> RenderResult:
    """Re-clobber every managed path from the package and regenerate. ``force`` skips the guard."""
    return apply(repo_root, force=force)
