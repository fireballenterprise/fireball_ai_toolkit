"""Renderer helpers: frontmatter emission + allowed-tools derivation."""

from __future__ import annotations

from pathlib import Path

import pytest

from fireball_ai_toolkit.catalog import Command
from fireball_ai_toolkit.renderers._common import derive_allowed_tools, render_frontmatter

pytestmark = pytest.mark.ai_toolkit


def _command(body: str, *, allowed=()) -> Command:
    return Command(
        slug="x",
        description="d",
        argument_hint="",
        body=body,
        source=Path("x.md"),
        allowed_tools=tuple(allowed),
    )


def test_render_frontmatter_skips_empty_and_quotes_unsafe():
    block = render_frontmatter({"name": "git", "description": "Use when: careful", "applyTo": ""})
    assert "name: git" in block
    assert 'description: "Use when: careful"' in block  # colon-space forces quoting
    assert "applyTo" not in block


def test_render_frontmatter_list_becomes_block_sequence():
    block = render_frontmatter({"hints": ["the repos", "all repos"]})
    assert block == "hints:\n  - the repos\n  - all repos"


def test_derive_allowed_tools_uv():
    assert derive_allowed_tools(_command("!`uv run --no-sync invoke fix`")) == ["Bash(uv run --no-sync *)"]


def test_derive_allowed_tools_aws_profile():
    tools = derive_allowed_tools(_command('!`AWS_PROFILE=fbe uv run --no-sync python -m modules.x.route "$A"`'))
    assert tools == ["Bash(AWS_PROFILE=fbe uv run --no-sync *)", "Bash(uv run --no-sync *)"]


def test_derive_allowed_tools_setup_script():
    assert derive_allowed_tools(_command("!`./setup.sh`")) == ["Bash(./setup.sh)"]


def test_derive_allowed_tools_prose_only():
    assert derive_allowed_tools(_command("Read the instructions and follow them.")) == []


def test_derive_allowed_tools_explicit_override_wins():
    cmd = _command("!`uv run --no-sync invoke x`", allowed=["Bash(gh pr create *)"])
    assert derive_allowed_tools(cmd) == ["Bash(gh pr create *)"]
