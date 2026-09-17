"""Verify `.github/instructions/*.md` files don't use `---` as a body section divider.

See .github/instructions/markdown.instructions.md — `---` is reserved for the YAML frontmatter
delimiter only; headers and blank lines alone provide enough visual separation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.style

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTRUCTIONS_DIR = REPO_ROOT / ".github" / "instructions"


def _stray_dividers(path: Path) -> list[int]:
    """Return line numbers (1-indexed) of standalone `---` lines outside frontmatter/code fences."""
    lines = path.read_text().splitlines()
    stray: list[int] = []
    in_fence = False
    frontmatter_done = False
    skip_next_frontmatter_close = lines[:1] == ["---"]

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if i == 1 and skip_next_frontmatter_close:
            continue
        if skip_next_frontmatter_close and not frontmatter_done:
            if stripped == "---":
                frontmatter_done = True
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped == "---":
            stray.append(i)
    return stray


def test_no_stray_horizontal_rules_in_instructions() -> None:
    offenders = {}
    for path in sorted(INSTRUCTIONS_DIR.glob("*.md")):
        stray = _stray_dividers(path)
        if stray:
            offenders[path.relative_to(REPO_ROOT).as_posix()] = stray
    assert not offenders, f"Stray `---` body dividers found (see markdown.instructions.md): {offenders}"
