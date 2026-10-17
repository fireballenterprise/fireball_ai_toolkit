"""``migrate_skills`` — a repo's own commands/ folded into skills/."""

from __future__ import annotations

from pathlib import Path

import pytest

from fireball_ai_toolkit.catalog import load_bundle
from fireball_ai_toolkit.cli import main
from fireball_ai_toolkit.migrate import migrate_skills

pytestmark = pytest.mark.ai_toolkit


def _tree(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): p.read_text() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "my_repo"
    local = repo / ".my_repo"
    (local / "commands").mkdir(parents=True)
    (local / "skills").mkdir()
    (local / "instructions").mkdir()
    (local / "commands" / "deploy.md").write_text(
        "---\nname: deploy\ndescription: Deploy it\nargument-hint: <env>\nagent: agent\n---\n\n"
        '!`uv run --no-sync invoke deploy "$ARGUMENTS"`\n\nThen verify.\n'
    )
    (local / "commands" / "deploy_all.md").write_text(
        "---\nname: deploy_all\ndescription: Alias\nargument-hint: none\nagent: agent\n---\n\nSee deploy.\n"
    )
    (local / "skills" / "deploy.md").write_text(
        "---\nname: deploy\ndescription: Use for deploys. Equivalent to /deploy.\nhints:\n  - ship it\n"
        "instructions:\n  - .my_repo/instructions/deploy.md\n"
        "commands:\n  - .my_repo/commands/deploy.md\n  - .my_repo/commands/deploy_all.md\n---\n"
    )
    (local / "instructions" / "deploy.md").write_text(
        "# Deploy\n\nRun `.my_repo/commands/deploy.md`.\nAlso see .github/prompts/deploy.prompt.md.\n"
    )
    return repo


def test_merges_commands_into_skills(repo: Path):
    report = migrate_skills(repo)
    local = repo / ".my_repo"
    assert not (local / "commands").exists()
    assert report.merged == ["deploy", "deploy_all"]

    skills = {s.name: s for s in load_bundle(canonical_root=repo / "none", local_root=local).skills}
    deploy = skills["deploy"]
    assert deploy.description == "Use for deploys. Equivalent to /deploy."  # skill header wins
    assert deploy.argument_hint == "<env>"
    assert deploy.hints == ("ship it",)
    assert deploy.instructions == (".my_repo/instructions/deploy.md", ".my_repo/skills/deploy_all.md")
    assert deploy.body.endswith("Then verify.")
    assert deploy.exec_line.startswith("uv run")
    assert (deploy.user_invocable, deploy.ai_invocable) == (True, True)
    text = (local / "skills" / "deploy.md").read_text()
    assert "user-invocable" not in text
    assert "name:" not in text
    assert "agent:" not in text
    assert skills["deploy_all"].body == "See deploy."


def test_rewrites_safe_references_and_reports_the_rest(repo: Path):
    report = migrate_skills(repo)
    doc = (repo / ".my_repo" / "instructions" / "deploy.md").read_text()
    assert "`.my_repo/skills/deploy.md`" in doc
    assert report.rewritten == [".my_repo/instructions/deploy.md"]
    assert any("deploy.prompt.md" in item for item in report.manual)


def test_dry_run_changes_nothing(repo: Path):
    before = _tree(repo)
    report = migrate_skills(repo, dry_run=True)
    assert _tree(repo) == before
    assert report.merged == ["deploy", "deploy_all"]
    assert report.removed_commands_dir
    assert report.lines()[0].startswith("[dry-run] would merge")


def test_second_run_is_a_noop(repo: Path):
    migrate_skills(repo)
    after = _tree(repo)
    report = migrate_skills(repo)
    assert not report.changed
    assert _tree(repo) == after


def test_existing_body_is_never_overwritten(repo: Path):
    (repo / ".my_repo" / "skills" / "deploy.md").write_text("---\ndescription: d\n---\n\nalready merged\n")
    report = migrate_skills(repo)
    assert (repo / ".my_repo" / "skills" / "deploy.md").read_text().endswith("already merged\n")
    assert any(item.startswith("deploy:") for item in report.skipped)
    assert (repo / ".my_repo" / "commands" / "deploy.md").exists()  # kept for a hand merge
    assert report.merged == ["deploy_all"]


def test_cli_dry_run_then_apply_runs_it(repo: Path, capsys: pytest.CaptureFixture[str]):
    assert main(["--repo", str(repo), "migrate-skills", "--dry-run"]) == 0
    assert (repo / ".my_repo" / "commands").exists()
    assert "[dry-run]" in capsys.readouterr().out

    from fireball_ai_toolkit.apply import apply

    apply(repo)
    assert not (repo / ".my_repo" / "commands").exists()
    assert (repo / ".claude" / "skills" / "deploy" / "SKILL.md").is_file()
    assert (repo / ".github" / "skills" / "deploy_all" / "SKILL.md").is_file()
