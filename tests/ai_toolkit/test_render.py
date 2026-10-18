"""Rendering the canonical bundle into every provider view."""

from __future__ import annotations

from pathlib import Path

import pytest

from fireball_ai_toolkit.catalog import packaged_ai_root
from fireball_ai_toolkit.render import render_repo
from fireball_ai_toolkit.renderers import GENERATED_HEADER

pytestmark = pytest.mark.ai_toolkit


def _mini_content(root: Path) -> Path:
    """A tiny canonical tree: 3 flat skills (uv / aws / no-exec), 1 bundle skill, 2 instructions."""
    content = root / "content"
    (content / "instructions").mkdir(parents=True)
    skills = content / "skills"
    skills.mkdir(parents=True)

    (skills / "fix.md").write_text(
        "---\ndescription: Auto-fix lint\nargument-hint: none\n---\n\n!`uv run --no-sync invoke fix`\n"
    )
    (skills / "bedrock.md").write_text(
        "---\ndescription: Check models\nargument-hint: none\nai-invocable: false\n---\n\n"
        '!`AWS_PROFILE=fireballenterprise uv run --no-sync python -m modules.bedrock.route "$ARGUMENTS"`\n'
    )
    (skills / "repos.md").write_text(
        "---\ndescription: Repo map skill\nargument-hint: none\nuser-invocable: false\nhints:\n  - the repos\n"
        "instructions:\n  - .fireball_ai_toolkit/instructions/git.md\n---\n\n"
        "Show the repo map. Skill text here.\n"
    )
    (skills / "big" / "scripts").mkdir(parents=True)
    (skills / "big" / "SKILL.md").write_text("---\ndescription: Bundle skill\n---\n\nRun scripts/go.sh\n")
    (skills / "big" / "scripts" / "go.sh").write_text("echo go\n")
    (skills / "big" / ".dot").write_text("skip me\n")
    (content / "instructions" / "git.md").write_text(
        '---\ndescription: "Branch + PR rules"\n---\n# Git & PR Instructions\n\nBranch naming rules.\n'
    )
    (content / "instructions" / "python.md").write_text(
        '---\ndescription: "Python rules"\napplyTo: "**/*.py"\n---\n# Python\n\nType hints everywhere.\n'
    )
    return content


def test_every_renderer_produces_output(tmp_path):
    result = render_repo(tmp_path, canonical_root=packaged_ai_root())
    produced = {p.relative_to(tmp_path).parts[0] for p in result.written}
    assert {".github", ".claude", ".clinerules", ".sidecar", "AGENTS.md", "CLAUDE.md"} <= produced
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".claude" / "skills" / "fix" / "SKILL.md").exists()
    assert not (tmp_path / ".claude" / "commands").exists()
    assert not (tmp_path / ".github" / "prompts").exists()
    assert not (tmp_path / ".sidecar" / "commands").exists()
    assert (tmp_path / ".sidecar" / "skills" / "fix.md").exists()
    assert not (tmp_path / ".sidecar" / "skills" / "fix").exists()


def test_generated_header_on_every_markdown_file(tmp_path):
    for path in render_repo(tmp_path, canonical_root=packaged_ai_root()).written:
        if path.suffix == ".md":
            assert GENERATED_HEADER in path.read_text(encoding="utf-8"), path


def test_skill_md_carries_the_full_text_with_matching_frontmatter(tmp_path):
    render_repo(tmp_path, canonical_root=_mini_content(tmp_path))
    for root in (".claude", ".github"):
        text = (tmp_path / root / "skills" / "fix" / "SKILL.md").read_text()
        fm = text.split("---")[1]
        assert "name: fix" in fm
        assert "description: Auto-fix lint" in fm
        assert "argument-hint: none" in fm
        assert "user-invocable: true" in fm  # explicit even at the default
        assert "disable-model-invocation: false" in fm
        assert "!`uv run --no-sync invoke fix`" in text  # the full command text
        assert "Source of truth: `.fireball_ai_toolkit/skills/fix.md`" in text


def test_switches_render_to_provider_keys(tmp_path):
    render_repo(tmp_path, canonical_root=_mini_content(tmp_path))
    for root in (".claude", ".github"):
        bedrock = (tmp_path / root / "skills" / "bedrock" / "SKILL.md").read_text().split("---")[1]
        assert "disable-model-invocation: true" in bedrock
        assert "user-invocable: true" in bedrock
        repos = (tmp_path / root / "skills" / "repos" / "SKILL.md").read_text().split("---")[1]
        assert "user-invocable: false" in repos
        assert "disable-model-invocation: false" in repos


def test_skill_hints_and_instructions_are_materialised_in_the_body(tmp_path):
    render_repo(tmp_path, canonical_root=_mini_content(tmp_path))
    for root in (".claude", ".github"):
        text = (tmp_path / root / "skills" / "repos" / "SKILL.md").read_text()
        fm, body = text.split("---")[1], text.split("---", 2)[2]
        assert "hints" not in fm
        assert "instructions" not in fm
        assert "Skill text here." in body
        assert "- the repos" in body
        assert "- `.fireball_ai_toolkit/instructions/git.md`" in body


def test_claude_allowed_tools_are_derived(tmp_path):
    render_repo(tmp_path, canonical_root=_mini_content(tmp_path))
    fix = (tmp_path / ".claude" / "skills" / "fix" / "SKILL.md").read_text()
    assert "allowed-tools: Bash(uv run --no-sync *)" in fix

    bedrock = (tmp_path / ".claude" / "skills" / "bedrock" / "SKILL.md").read_text()
    assert "Bash(AWS_PROFILE=fireballenterprise uv run --no-sync *)" in bedrock
    assert "Bash(uv run --no-sync *)" in bedrock

    repos = (tmp_path / ".claude" / "skills" / "repos" / "SKILL.md").read_text()
    assert "allowed-tools" not in repos  # prose-only skill
    assert "allowed-tools" not in (tmp_path / ".github" / "skills" / "fix" / "SKILL.md").read_text()


def test_bundle_resources_are_copied_and_dotfiles_skipped(tmp_path):
    canonical = _mini_content(tmp_path)
    render_repo(tmp_path, canonical_root=canonical)
    for root in (".claude", ".github"):
        folder = tmp_path / root / "skills" / "big"
        assert (folder / "SKILL.md").is_file()
        assert (folder / "scripts" / "go.sh").read_text() == "echo go\n"
        assert not (folder / ".dot").exists()

    # a resource removed from the bundle disappears from the generated folders
    (canonical / "skills" / "big" / "scripts" / "go.sh").unlink()
    render_repo(tmp_path, canonical_root=canonical)
    for root in (".claude", ".github"):
        assert not (tmp_path / root / "skills" / "big" / "scripts").exists()
        assert (tmp_path / root / "skills" / "big" / "SKILL.md").is_file()


def test_cline_lists_user_invocable_skills_as_pointers(tmp_path):
    render_repo(tmp_path, canonical_root=_mini_content(tmp_path))
    fix = (tmp_path / ".clinerules" / "workflows" / "fix.md").read_text()
    assert "!`" not in fix
    assert "Source of truth: `.fireball_ai_toolkit/skills/fix.md`" in fix
    assert not (tmp_path / ".clinerules" / "workflows" / "repos.md").exists()  # user-invocable: false


def test_agents_index_lists_every_instruction_and_skill(tmp_path):
    render_repo(tmp_path, canonical_root=_mini_content(tmp_path))
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "`.fireball_ai_toolkit/instructions/git.md`" in agents
    assert "`.fireball_ai_toolkit/instructions/python.md`" in agents
    assert "**Git & PR**" in agents  # label derived from the H1
    assert "`/fix`" in agents
    assert "`/repos`" not in agents


def test_copilot_index_describes_skills_not_prompts(tmp_path):
    render_repo(tmp_path, canonical_root=_mini_content(tmp_path))
    index = (tmp_path / ".github" / "copilot-instructions.md").read_text()
    assert ".github/skills/" in index
    assert "prompt" not in index.lower()
    assert "commands" not in index.lower()


def test_sidecar_gets_flat_snake_case_skills_and_instruction_pointers(tmp_path):
    canonical = _mini_content(tmp_path)
    (canonical / "skills" / "add-bug.md").write_text(
        "---\ndescription: File a bug\nargument-hint: text\nhints:\n  - add bug\nai-invocable: false\n---\n\nBody here\n"
    )
    render_repo(tmp_path, canonical_root=canonical)
    skills = tmp_path / ".sidecar" / "skills"
    bug = (skills / "add_bug.md").read_text()
    assert "name: add_bug" in bug and "user-invocable: true" in bug and "disable-model-invocation: true" in bug
    assert "  - add bug" in bug and "  - add-bug" in bug and "Body here" in bug
    assert "Source of truth: `.fireball_ai_toolkit/skills/add-bug.md`" in bug
    assert "name: fix" in (skills / "fix.md").read_text()
    assert (skills / "big.md").is_file() and not (skills / "big").exists()  # bundle: main body only
    assert not list(skills.rglob("SKILL.md"))
    inst = (tmp_path / ".sidecar" / "instructions" / "python.md").read_text()
    assert 'applyTo: "**/*.py"' in inst
    assert "Source of truth: `.fireball_ai_toolkit/instructions/python.md`" in inst


def test_instruction_stubs_stay_pointers(tmp_path):
    render_repo(tmp_path, canonical_root=_mini_content(tmp_path))
    inst = (tmp_path / ".github" / "instructions" / "python.instructions.md").read_text()
    assert "Type hints everywhere." not in inst
    assert "Source of truth: `.fireball_ai_toolkit/instructions/python.md`" in inst
    assert 'applyTo: "**/*.py"' in inst


def test_old_generated_commands_and_prompts_are_removed(tmp_path):
    for rel in (
        ".claude/commands/fix.md",
        ".github/prompts/fix.prompt.md",
        ".sidecar/commands/fix.md",
        ".sidecar/skills/fix/SKILL.md",
        ".sidecar/skills/old_gone.md",
    ):
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"{GENERATED_HEADER}\nold\n")
    hand = tmp_path / ".claude" / "commands" / "mine.md"
    hand.write_text("hand written\n")
    render_repo(tmp_path, canonical_root=_mini_content(tmp_path))
    assert not (tmp_path / ".claude/commands/fix.md").exists()
    assert not (tmp_path / ".github/prompts").exists()
    assert not (tmp_path / ".sidecar/commands").exists()
    assert not (tmp_path / ".sidecar/skills/old_gone.md").exists()
    assert not (tmp_path / ".sidecar/skills/fix").exists()
    assert "name: fix" in (tmp_path / ".sidecar/skills/fix.md").read_text()
    assert hand.exists()  # never touch a hand-written file


def test_local_overlay_overrides_and_adds(tmp_path):
    canonical = _mini_content(tmp_path)
    local = tmp_path / f".{tmp_path.name}"  # the local layer dir is named after the repo folder
    (local / "skills").mkdir(parents=True)
    (local / "skills" / "fix.md").write_text(
        "---\ndescription: LOCAL fix\nargument-hint: none\n---\n\n!`./setup.sh`\n"
    )
    (local / "skills" / "deploy.md").write_text(
        "---\ndescription: repo-only deploy\nargument-hint: none\n---\n\n!`uv run --no-sync invoke deploy`\n"
    )
    render_repo(tmp_path, canonical_root=canonical)

    fix = (tmp_path / ".claude" / "skills" / "fix" / "SKILL.md").read_text()
    assert "description: LOCAL fix" in fix
    assert f"Source of truth: `.{tmp_path.name}/skills/fix.md`" in fix  # pointer -> the local layer
    assert "allowed-tools: Bash(./setup.sh)" in fix
    assert (tmp_path / ".claude" / "skills" / "deploy" / "SKILL.md").exists()
    assert (tmp_path / ".github" / "skills" / "deploy" / "SKILL.md").exists()


def test_dropped_slug_is_cleaned_on_rerender(tmp_path):
    canonical = _mini_content(tmp_path)
    render_repo(tmp_path, canonical_root=canonical)
    assert (tmp_path / ".claude" / "skills" / "bedrock" / "SKILL.md").exists()

    (canonical / "skills" / "bedrock.md").unlink()
    render_repo(tmp_path, canonical_root=canonical)
    assert not (tmp_path / ".claude" / "skills" / "bedrock").exists()
    assert not (tmp_path / ".github" / "skills" / "bedrock").exists()
    assert (tmp_path / ".claude" / "skills" / "fix" / "SKILL.md").exists()


def test_underscore_local_skill_renders_normalised_with_original_hint(tmp_path):
    local = tmp_path / f".{tmp_path.name}"
    (local / "skills").mkdir(parents=True)
    (local / "skills" / "add_size_chart.md").write_text("---\ndescription: charts\n---\n\nDo charts.\n")
    render_repo(tmp_path, canonical_root=_mini_content(tmp_path))

    for root in (".claude", ".github"):
        text = (tmp_path / root / "skills" / "add-size-chart" / "SKILL.md").read_text()
        assert "name: add-size-chart" in text.split("---")[1]
        assert "- add_size_chart" in text  # the original spelling is a trigger phrase
        assert f"Source of truth: `.{tmp_path.name}/skills/add_size_chart.md`" in text
        assert not (tmp_path / root / "skills" / "add_size_chart").exists()
    assert (tmp_path / ".clinerules" / "workflows" / "add-size-chart.md").exists()
    assert "`/add-size-chart`" in (tmp_path / "AGENTS.md").read_text()
