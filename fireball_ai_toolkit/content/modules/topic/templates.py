"""Template generators for per-topic thin-pointer instruction files."""

from __future__ import annotations

import logging
from collections.abc import Sequence

LOGGER = logging.getLogger(__name__)


def render_agents_md(
    topic_path: str,
    description: str | None = None,
    instructions: Sequence[str] | None = None,
    body: str | None = None,
) -> str:
    """Return the AGENTS.md content for a topic at `topic_path` (e.g. "fireball_3d").

    `instructions` is a list of `.github/instructions/` slugs (without the
    `.instructions.md` suffix) whose top-level rules apply to work in this topic —
    rendered as an "## Instructions" section so an agent opening the topic knows
    which project instructions to read first. `body` is free-form Markdown appended
    after the standard sections for topic-specific guidance that doesn't belong in a
    one-line description. All three are persisted in `topics/topics_list.yml`'s
    `topic_meta:` map so `/topic update` regenerates them instead of wiping them.
    """
    # `topics/<path>/AGENTS.md` -> repo root: one `../` per path segment, plus one for `topics/`.
    up = "../" * (topic_path.count("/") + 2)
    name = topic_path.rsplit("/", maxsplit=1)[-1]

    lines = [f"# Agent Instructions — {name}", ""]
    if description:
        lines.extend([description, ""])
    lines.extend(
        [
            f"This topic's rules live in `{up}.github/instructions/topics.instructions.md`. Read it",
            "before starting or continuing planning work here.",
            "",
        ]
    )
    if instructions:
        lines.append("## Instructions")
        lines.append("")
        lines.append(
            "Read these top-level project instructions in full before working on anything in this "
            "topic — they are the canonical source for architecture, workflows, and constraints, "
            "not the historical chats here:"
        )
        lines.append("")
        for slug in instructions:
            lines.append(f"- [`{slug}`]({up}.github/instructions/{slug}.instructions.md)")
        lines.append("")
    lines.extend(
        [
            "- Chats: `chats/` (`YYYYMMDD_slug.md` dated planning sessions, see `/chat`; "
            "`00000000_session_memory.md` is the standing per-topic resume pointer — read it first)",
            "- Plans: `plans/` (`YYYYMMDD_slug.md` living design docs — see `plans.instructions.md`)",
            "- Docs: `docs/` (user-facing reference material — only created on explicit request)",
        ]
    )
    if body:
        lines.extend(["", body.strip()])
    return "\n".join(lines) + "\n"


def render_claude_md() -> str:
    """Return the CLAUDE.md content for any topic — a one-line pointer to AGENTS.md."""
    return "See `AGENTS.md`.\n"
