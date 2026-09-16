"""The packaged canonical content tree is normalised to the house Markdown style.

`fireball_ai_toolkit.mdfix` (blank-line-after-header, stray `---` divider in instruction
bodies) is the enforcement; this test keeps `content/` itself clean so an `apply` never
introduces drift. See `content/instructions/markdown.md`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fireball_ai_toolkit.catalog import packaged_content_root
from fireball_ai_toolkit.mdfix import fix_tree, normalize

pytestmark = pytest.mark.style

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_packaged_content_is_normalised() -> None:
    offenders = [
        p.relative_to(packaged_content_root()).as_posix()
        for p in fix_tree(packaged_content_root(), write=False)
    ]
    assert not offenders, f"content/ not normalised — run `invoke fix`: {offenders}"


def test_repo_docs_are_normalised() -> None:
    for name in ("README.md", "DESIGN.md"):
        path = REPO_ROOT / name
        assert normalize(path.read_text(encoding="utf-8")) == path.read_text(encoding="utf-8"), name
