"""modules.toolkit.repo.family + get_family_repos — nested + legacy schema, scope, retired."""

import pytest
from modules.toolkit.repo import family
from modules.toolkit.setup import properties

pytestmark = pytest.mark.repo


def _clone(base, name):
    (base / name / ".git").mkdir(parents=True)


_NESTED = {
    "acme": {
        "root": {
            "ai": False,
            "default_branch": "main",
            "parent": "none",
            "pull_request": True,
            "purpose": "r",
            "status": "active",
            "use_ci": True,
            "visibility": "public",
        },
        "midtool": {
            "ai": True,
            "default_branch": "main",
            "parent": "root",
            "purpose": "m",
            "status": "active",
            "visibility": "public",
        },
        "app": {
            "ai": False,
            "default_branch": "development",
            "parent": "root",
            "purpose": "a",
            "status": "active",
            "visibility": "private",
        },
        "old": {
            "ai": False,
            "default_branch": "main",
            "parent": "none",
            "purpose": "o",
            "status": "retired",
            "visibility": "private",
        },
    },
    "lb": {
        "me": {
            "ai": True,
            "default_branch": "main",
            "parent": "midtool",
            "purpose": "mine",
            "status": "active",
            "visibility": "private",
        },
    },
}


@pytest.fixture
def nested(tmp_path, monkeypatch):
    for org, repos in _NESTED.items():
        for name in repos:
            _clone(tmp_path / org, name)
    props = {
        "repos": _NESTED,
        "repos_local": {"acme": str(tmp_path / "acme"), "lb": str(tmp_path / "lb")},
        "repo": {"local": str(tmp_path / "lb" / "me")},
    }
    monkeypatch.setattr(properties, "get_properties", lambda: props)
    monkeypatch.setattr(properties, "get_repo_local", lambda: tmp_path / "lb" / "me")
    return tmp_path


def test_nested_schema_parent_depth_order_and_self(nested):
    repos = properties.get_family_repos(include_self=True, include_retired=True)
    # depth 0: old, root · depth 1: app, midtool · depth 2: me
    assert [r.name for r in repos] == ["old", "root", "app", "midtool", "me"]
    me = repos[-1]
    assert me.is_self and me.parent == "midtool" and me.ai is True


def test_retired_excluded_by_default(nested):
    assert "old" not in {r.name for r in properties.get_family_repos(include_retired=False)}
    assert "old" in {r.name for r in properties.get_family_repos(include_retired=True)}


def test_scope_ai_and_dev_prd(nested):
    assert {r.name for r in properties.get_family_repos(scope="ai")} == {"midtool"}  # me is self
    assert {r.name for r in properties.get_family_repos(scope="dev_prd")} == {"app"}


def test_dev_prd_property_from_default_branch(nested):
    app = next(r for r in properties.get_family_repos() if r.name == "app")
    assert app.dev_prd is True
    root = next(r for r in properties.get_family_repos() if r.name == "root")
    assert root.dev_prd is False


def test_ci_and_pr_flags_default_false(nested):
    by_name = {r.name: r for r in properties.get_family_repos(include_self=True, include_retired=True)}
    assert by_name["root"].use_ci is True and by_name["root"].pull_request is True
    assert by_name["me"].use_ci is False and by_name["me"].pull_request is False  # keys absent → False


def test_find_current_repo_and_print_self(nested, capsys):
    me = properties.find_current_repo()
    assert me is not None and me.name == "me" and me.pull_request is False
    assert family.print_self() == 0
    out = capsys.readouterr().out
    assert "acme/me" not in out and "lb/me" in out
    assert "no PR" in out and "local invoke tasks" in out


def test_legacy_list_plus_lineage_still_parses(tmp_path, monkeypatch):
    _clone(tmp_path / "acme", "template_python")
    _clone(tmp_path / "acme", "proj")
    props = {
        "repos": {"acme": ["template_python", "proj"], "lineage": {"template_python": ["proj"]}},
        "repos_local": {"acme": str(tmp_path / "acme")},
        "repo": {"local": str(tmp_path / "acme" / "template_python")},
    }
    monkeypatch.setattr(properties, "get_properties", lambda: props)
    monkeypatch.setattr(properties, "get_repo_local", lambda: tmp_path / "acme" / "template_python")
    repos = properties.get_family_repos(include_self=True)
    assert [(r.name, r.parent) for r in repos] == [("template_python", None), ("proj", "template_python")]


def test_no_repos_key_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(properties, "get_properties", lambda: {"repo": {"local": str(tmp_path)}})
    monkeypatch.setattr(properties, "get_repo_local", lambda: tmp_path)
    assert properties.get_family_repos() == []


def test_run_family_singleton_fallback(monkeypatch, capsys):
    monkeypatch.setattr(family, "get_family_repos", lambda **_kw: [])
    dispatched = []
    monkeypatch.setattr(family, "_dispatch_single", lambda verb: dispatched.append(verb) or 0)
    assert family.run_family("pull", scope="ai") == 0
    assert dispatched == ["pull"]
    assert "family run requested" in capsys.readouterr().out


def test_print_map_without_family(monkeypatch, capsys):
    monkeypatch.setattr(family, "get_family_repos", lambda **_kw: [])
    assert family.print_map() == 0
    assert "no related-repo family" in capsys.readouterr().out
