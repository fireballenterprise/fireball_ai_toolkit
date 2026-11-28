"""`--scope` on repo.pull / push / sync / cleanup (orchestrator#253): all | ai | dev_prd | repo names from `properties.yml`."""

from pathlib import Path

import pytest
from modules.fireball_ai_toolkit.setup import properties
from modules.fireball_ai_toolkit.setup.properties import FamilyRepo


def _repo(name, org="acme", exists=True):
    return FamilyRepo(
        org=org, name=name, path=Path(name), is_self=False, exists=exists, default_branch="main", parent=None,
        status="active", visibility="", ai=False, use_ci=False, pull_request=False, purpose="",
    )  # fmt: skip


@pytest.fixture(name="family")
def fixture_family(monkeypatch):
    repos = [_repo("root"), _repo("kit"), _repo("sidecar"), _repo("gone", exists=False)]
    monkeypatch.setattr(properties, "get_family_repos", lambda **kw: repos if kw.get("include_missing") else repos[:3])
    return repos


def test_named_repos_come_back_root_to_leaf(family):
    assert [r.name for r in properties.select_family("sidecar,root")] == ["root", "sidecar"]
    assert [r.name for r in properties.select_family("acme/kit")] == ["kit"]


def test_all_is_the_whole_family(family):
    assert [r.name for r in properties.select_family("all")] == ["root", "kit", "sidecar"]
    assert [r.name for r in properties.select_family(None)] == ["root", "kit", "sidecar"]


def test_an_unknown_or_missing_name_is_refused_with_the_valid_ones(family):
    with pytest.raises(ValueError, match="unknown repo.*nope.*one or more of: gone, kit, root, sidecar"):
        properties.select_family("nope")
    with pytest.raises(ValueError, match="not cloned on this machine: gone"):
        properties.select_family("gone")
