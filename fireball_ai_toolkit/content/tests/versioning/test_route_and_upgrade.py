"""versioning/route.py repo-task dispatch + upgrade.py's corrupt-SDKMAN-archive recovery."""

import subprocess
import sys
from types import SimpleNamespace

import pytest
from modules.fireball_ai_toolkit.versioning import route, sdkman, upgrade

pytestmark = pytest.mark.versioning


def _run_route(monkeypatch, argv, *, has_task, calls):
    monkeypatch.setattr(sys, "argv", ["route", *argv])
    monkeypatch.setattr(route, "resolve_target_repo", lambda _t: None)
    monkeypatch.setattr(route, "_repo_has_task", lambda name: has_task)
    monkeypatch.setattr(route.subprocess, "run", lambda cmd, **_k: calls.append(cmd) or SimpleNamespace(returncode=0))
    return route.main()


def test_route_uses_repo_invoke_task_when_defined(monkeypatch):
    calls = []
    assert _run_route(monkeypatch, ["upgrade cdk --yes"], has_task=True, calls=calls) == 0
    assert calls == [["uv", "run", "--no-sync", "invoke", "versioning.upgrade", "--only", "cdk", "--yes"]]


def test_route_check_cdk_accepted(monkeypatch):
    calls = []
    _run_route(monkeypatch, ["check cdk --dry-run"], has_task=True, calls=calls)
    assert calls[0][-3:] == ["--only", "cdk", "--dry-run"]


def test_route_falls_back_to_shared_module_without_repo_task(monkeypatch):
    calls = []
    _run_route(monkeypatch, ["check libs --yes"], has_task=False, calls=calls)
    assert calls[0][:5] == ["uv", "run", "--no-sync", "python", "-m"]
    assert calls[0][5].endswith("versioning.check")
    assert calls[0][6:] == ["--only", "libs", "--yes"]


def test_route_cdk_without_repo_task_is_an_error(monkeypatch):
    calls = []
    assert _run_route(monkeypatch, ["upgrade cdk"], has_task=False, calls=calls) == 1
    assert not calls


def test_repo_has_task_parses_invoke_list(monkeypatch):
    out = "Available tasks:\n\n  versioning.check   x\n  versioning.upgrade y\n"
    monkeypatch.setattr(route.subprocess, "run", lambda *_a, **_k: SimpleNamespace(returncode=0, stdout=out))
    assert route._repo_has_task("versioning.check")
    assert not route._repo_has_task("versioning.bump")


def test_repo_has_task_false_when_probe_fails(monkeypatch):
    def boom(*_a, **_k):
        raise subprocess.TimeoutExpired("uv", 1)

    monkeypatch.setattr(route.subprocess, "run", boom)
    assert not route._repo_has_task("versioning.check")


def _sdk_home(tmp_path, monkeypatch, installed):
    home = tmp_path / "sdkman"
    for candidate, identifier in installed:
        (home / "candidates" / candidate / identifier).mkdir(parents=True)
    monkeypatch.setenv("SDKMAN_DIR", str(home))


def test_sdkman_install_skips_corrupt_release_repins_and_retries(tmp_path, monkeypatch):
    (tmp_path / ".sdkmanrc").write_text("# header\njava=26.0.2.1+1-tem\n", encoding="utf-8")
    _sdk_home(tmp_path, monkeypatch, [("java", "26.0.2-tem")])
    monkeypatch.setattr(
        sdkman, "available_identifiers", lambda _c: ["26.0.2.1+1-tem", "26.0.2-tem", "25.0.4-tem", "27.0.0-ea"]
    )
    runs = iter([(1, "Stop! The archive was corrupt"), (0, "ok")])
    seen = []
    monkeypatch.setattr(upgrade, "_run_sdk_env_install", lambda _p: seen.append(1) or next(runs))
    upgrade.sdkman_env_install(tmp_path)
    text = (tmp_path / ".sdkmanrc").read_text(encoding="utf-8")
    assert "# sdkman-skip: java 26.0.2.1+1-tem" in text
    assert "java=26.0.2-tem" in text
    assert "java=26.0.2.1+1-tem" not in text
    assert len(seen) == 2
    # and the skip survives a later /update: nothing newer than 26.0.2-tem that isn't skipped
    skip = sdkman.read_skip_list(tmp_path)["java"]
    assert sdkman.latest_identifier("java", "26.0.2-tem", skip) is None


def test_sdkman_install_success_does_not_touch_sdkmanrc(tmp_path, monkeypatch):
    (tmp_path / ".sdkmanrc").write_text("java=26.0.2-tem\n", encoding="utf-8")
    monkeypatch.setattr(upgrade, "_run_sdk_env_install", lambda _p: (0, ""))
    upgrade.sdkman_env_install(tmp_path)
    assert (tmp_path / ".sdkmanrc").read_text(encoding="utf-8") == "java=26.0.2-tem\n"


def test_sdkman_install_retries_only_once(tmp_path, monkeypatch):
    (tmp_path / ".sdkmanrc").write_text("java=26.0.2.1+1-tem\n", encoding="utf-8")
    _sdk_home(tmp_path, monkeypatch, [])
    monkeypatch.setattr(sdkman, "available_identifiers", lambda _c: ["26.0.2.1+1-tem", "26.0.2-tem"])
    calls = []
    monkeypatch.setattr(upgrade, "_run_sdk_env_install", lambda _p: calls.append(1) or (1, "boom"))
    upgrade.sdkman_env_install(tmp_path)
    assert len(calls) == 2


def test_sdkman_install_failure_with_everything_installed_does_not_repin(tmp_path, monkeypatch):
    (tmp_path / ".sdkmanrc").write_text("java=26.0.2-tem\n", encoding="utf-8")
    _sdk_home(tmp_path, monkeypatch, [("java", "26.0.2-tem")])
    calls = []
    monkeypatch.setattr(upgrade, "_run_sdk_env_install", lambda _p: calls.append(1) or (1, "x"))
    upgrade.sdkman_env_install(tmp_path)
    assert len(calls) == 1
    assert (tmp_path / ".sdkmanrc").read_text(encoding="utf-8") == "java=26.0.2-tem\n"
