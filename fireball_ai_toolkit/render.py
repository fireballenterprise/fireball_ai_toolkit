"""Run every renderer over a content bundle and report the files written."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .catalog import ContentBundle, load_bundle, local_layer_name, packaged_ai_root
from .renderers import ALL


@dataclass(frozen=True)
class RenderResult:
    written: list[Path]

    @property
    def by_count(self) -> int:
        return len(self.written)


def render_repo(
    repo_root: Path,
    *,
    canonical_root: Path | None = None,
    only: list[str] | None = None,
) -> RenderResult:
    """Regenerate every provider view in ``repo_root`` from ``.ai/toolkit`` + ``.ai/<repo>``.

    ``.ai/toolkit/`` comes from the packaged canonical tree (or ``canonical_root``); the local
    overlay ``.ai/<repo>/`` is read from ``repo_root`` when that directory exists.

    Args:
        repo_root: consuming repo root.
        canonical_root: override the packaged ``content/`` tree (tests / this repo itself).
        only: restrict to a subset of renderer names (``renderers.ALL`` keys).
    """
    repo_root = repo_root.resolve()
    local_name = local_layer_name(repo_root)
    local_dir = repo_root / ".ai" / local_name
    bundle: ContentBundle = load_bundle(
        canonical_root=canonical_root or packaged_ai_root(),
        local_root=local_dir if local_dir.is_dir() else None,
        local_name=local_name,
    )

    names = only or list(ALL)
    written: list[Path] = []
    for name in names:
        written.extend(ALL[name](bundle, repo_root))
    return RenderResult(written=sorted(set(written)))
