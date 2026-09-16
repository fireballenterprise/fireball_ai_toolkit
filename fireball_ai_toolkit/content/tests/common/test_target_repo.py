"""modules.toolkit.common.target_repo — the --repo selector + delegation, and its CI-safety."""

import subprocess
import sys

import pytest
from modules.toolkit.common import target_repo

pytestmark = pytest.mark.common


def test_none_is_a_noop_and_imports_nothing_heavy():
    assert target_repo.resolve_target_repo(None) is None
    assert target_repo.resolve_target_repo("   ") is None


def test_import_does_not_pull_in_properties_or_yaml():
    """Importing target_repo must stay stdlib-cheap — `versioning.bump` runs it in CI where
    properties.yml / yaml are unavailable."""
    code = (
        "import sys; import modules.toolkit.common.target_repo as t; "
        "bad=[m for m in sys.modules if m.endswith('setup.properties') or m=='yaml' "
        "or m.endswith('backlog.common')]; "
        "print('BAD' if bad else 'OK', bad)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.startswith("OK"), out.stdout


@pytest.mark.parametrize("token", ["./x", "../x", "/abs/x", "~/x", "a/b/c"])
def test_path_shaped_tokens_take_the_path_branch(tmp_path, monkeypatch, token):
    captured = {}
    monkeypatch.setattr(target_repo, "error", lambda msg, *a, **k: captured.setdefault("err", msg))
    target_repo.resolve_target_repo(token)
    assert "err" in captured  # no .git at that made-up path → error(), properties.yml untouched


def test_real_path_with_git_resolves(tmp_path):
    (tmp_path / ".git").mkdir()
    assert target_repo.resolve_target_repo(str(tmp_path)) == tmp_path.resolve()


def test_bare_name_without_family_map_errors_toward_a_path(monkeypatch):
    monkeypatch.setattr("modules.toolkit.setup.properties.get_family_repos", lambda **k: [])
    calls = []
    monkeypatch.setattr(
        target_repo, "error", lambda msg, *a, **k: calls.append(msg) or (_ for _ in ()).throw(SystemExit(1))
    )
    with pytest.raises(SystemExit):
        target_repo.resolve_target_repo("some_repo")
    assert "pass a filesystem path" in calls[0]


def test_delegate_picks_cwd_by_layout(tmp_path, monkeypatch):
    vendored = tmp_path / "vendored"
    (vendored / "modules" / "toolkit").mkdir(parents=True)
    plain = tmp_path / "plain"
    plain.mkdir()
    seen = {}
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kw: (
            seen.update(cwd=kw["cwd"], env_root=kw["env"]["SIDECAR_REPO_ROOT"]) or type("P", (), {"returncode": 0})()
        ),
    )
    target_repo.delegate(vendored, "versioning.check", [], caller_root=plain)
    assert seen["cwd"] == vendored and seen["env_root"] == str(vendored)
    target_repo.delegate(plain, "versioning.check", [], caller_root=tmp_path)
    assert seen["cwd"] == tmp_path and seen["env_root"] == str(plain)
