"""modules.toolkit.versioning.check — toolchain-aware sub-check selection + route parsing."""

import pytest
from modules.toolkit.versioning import check, route

pytestmark = pytest.mark.versioning


def _run_check(monkeypatch, tmp_path, argv):
    ran = []
    monkeypatch.setattr(check, "find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(check, "_run_one", lambda name, flags: ran.append((name, tuple(flags))) or 0)
    monkeypatch.setattr("sys.argv", ["check", *argv])
    try:
        check.main()
    except SystemExit as exc:
        return ran, (exc.code or 0)
    return ran, 0


def test_no_subarg_runs_only_detected_toolchains(monkeypatch, tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    ran, code = _run_check(monkeypatch, tmp_path, [])
    names = [name for name, _ in ran]
    assert names == ["libs", "python"]  # no workflows/, no .sdkmanrc
    assert code == 0


def test_only_forces_one_even_if_toolchain_absent(monkeypatch, tmp_path):
    ran, code = _run_check(monkeypatch, tmp_path, ["--only", "sdkman"])
    assert [name for name, _ in ran] == ["sdkman"]


def test_one_failing_subcheck_fails_overall(monkeypatch, tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    monkeypatch.setattr(check, "find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(check, "_run_one", lambda name, flags: 1 if name == "libs" else 0)
    monkeypatch.setattr("sys.argv", ["check"])
    with pytest.raises(SystemExit) as exc:
        check.main()
    assert exc.value.code == 1


def test_exit_3_from_a_subcheck_is_tolerated(monkeypatch, tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    monkeypatch.setattr(check, "find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(check, "_run_one", lambda name, flags: 3)
    monkeypatch.setattr("sys.argv", ["check"])
    check.main()  # no SystemExit


class _FakeProc:
    returncode = 0


@pytest.mark.parametrize(
    ("argv", "expect_repo", "expect_only"),
    [
        (["check"], None, None),
        (["check", "libs"], None, "libs"),
        (["check", "android"], "android", None),
        (["check", "--repo", "../x", "libs"], "../x", "libs"),
        (["check", "fireball_sidecar_android", "sdkman"], "fireball_sidecar_android", "sdkman"),
    ],
)
def test_route_peels_repo_and_subarg(monkeypatch, argv, expect_repo, expect_only):
    seen = {}

    def fake_resolve(tok):
        seen["repo"] = tok

    def fake_run(cmd, **_kw):
        seen["cmd"] = cmd
        return _FakeProc()

    monkeypatch.setattr(route, "resolve_target_repo", fake_resolve)
    monkeypatch.setattr(route.subprocess, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["route", *argv])
    route.main()

    assert seen["repo"] == expect_repo
    if expect_only:
        assert seen["cmd"][seen["cmd"].index("--only") + 1] == expect_only
    else:
        assert "--only" not in seen["cmd"]
