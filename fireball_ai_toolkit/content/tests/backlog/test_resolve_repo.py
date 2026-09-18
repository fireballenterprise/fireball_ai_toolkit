"""modules.fireball_ai_toolkit.backlog.common.resolve_repo — the fuzzy `--repo` matcher."""

from pathlib import Path

import pytest
from modules.fireball_ai_toolkit.backlog import common
from modules.fireball_ai_toolkit.setup.properties import FamilyRepo

pytestmark = pytest.mark.backlog


def _repo(name, purpose="", *, org="fireballenterprise", status="active", pull_request=False, branch="main"):
    return FamilyRepo(
        org=org,
        name=name,
        path=Path("/nonexistent") / name,
        is_self=False,
        exists=False,
        default_branch=branch,
        parent=None,
        status=status,
        visibility="private",
        ai=False,
        use_ci=False,
        pull_request=pull_request,
        purpose=purpose,
    )


_FAMILY = [
    _repo("fireball_sidecar_vscode", "First-party Fireball Sidecar VS Code extension"),
    _repo("fireball_sidecar_chat", "Multi-user chat app on AWS Bedrock", branch="development"),
    _repo("fireball_ai_toolkit", "Canonical shared AI-agent commands + generator", pull_request=True),
    _repo("fireball_orchestrator", "Orchestration hub for all Fireball Enterprise repos"),
    _repo("template_python", "Base Python project template", org="levonbecker"),
    _repo("product_metadata", "Shared product metadata", status="retired"),
]


@pytest.fixture(autouse=True)
def _family(monkeypatch):
    monkeypatch.setattr(common, "get_family_repos", lambda **_kw: list(_FAMILY))


def test_exact_name_and_org_name():
    assert common.resolve_repo("fireball_orchestrator").name == "fireball_orchestrator"
    assert common.resolve_repo("levonbecker/template_python").name == "template_python"


def test_unique_substring():
    assert common.resolve_repo("vscode").name == "fireball_sidecar_vscode"
    assert common.resolve_repo("orchestrator").name == "fireball_orchestrator"


def test_word_overlap_against_purpose():
    assert common.resolve_repo("the vscode extension").name == "fireball_sidecar_vscode"
    assert common.resolve_repo("chat app on bedrock").name == "fireball_sidecar_chat"


def test_retired_only_by_exact_name():
    assert common.resolve_repo("product_metadata").name == "product_metadata"
    with pytest.raises(SystemExit):
        common.resolve_repo("product")  # retired → not a fuzzy candidate


def test_ambiguous_exits_and_lists_candidates(capsys):
    with pytest.raises(SystemExit):
        common.resolve_repo("sidecar")
    printed = capsys.readouterr().out
    assert "fireball_sidecar_vscode" in printed and "fireball_sidecar_chat" in printed


def test_unknown_exits_with_the_active_list(capsys):
    with pytest.raises(SystemExit):
        common.resolve_repo("nonesuch")
    assert "fireball_orchestrator" in capsys.readouterr().out
