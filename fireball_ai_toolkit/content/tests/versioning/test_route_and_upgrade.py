"""versioning/route.py repo-task dispatch + upgrade.py's corrupt-SDKMAN-archive recovery."""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from modules.fireball_ai_toolkit.versioning import python as py_mod
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


_REAL_CANDIDATE_RUNS = upgrade._candidate_runs
_REAL_ENSURE_NATIVE = upgrade.ensure_native_sdkman_platform


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


@pytest.fixture(autouse=True)
def _installs_run_by_default(monkeypatch):
    monkeypatch.setattr(upgrade, "_candidate_runs", lambda _c, _i: True)
    monkeypatch.setattr(upgrade, "ensure_native_sdkman_platform", lambda: False)


def test_sdkman_broken_install_is_removed_and_reinstalled_natively(tmp_path, monkeypatch):
    (tmp_path / ".sdkmanrc").write_text("java=26.0.2-tem\n", encoding="utf-8")
    _sdk_home(tmp_path, monkeypatch, [("java", "26.0.2-tem")])
    state = {"reinstalled": False}

    def runs(_c, _i):
        return state["reinstalled"]

    def install(_p):
        # the reinstall recreates the dir (natively) and it now runs
        assert not (tmp_path / "sdkman" / "candidates" / "java" / "26.0.2-tem").exists()
        (tmp_path / "sdkman" / "candidates" / "java" / "26.0.2-tem").mkdir(parents=True)
        state["reinstalled"] = True
        return 0, "ok"

    monkeypatch.setattr(upgrade, "_candidate_runs", runs)
    monkeypatch.setattr(upgrade, "_run_sdk_env_install", install)
    upgrade.sdkman_env_install(tmp_path)
    assert (tmp_path / ".sdkmanrc").read_text(encoding="utf-8") == "java=26.0.2-tem\n"


def test_sdkman_still_broken_after_reinstall_is_skipped_with_reason_and_repinned(tmp_path, monkeypatch):
    (tmp_path / ".sdkmanrc").write_text("java=26.0.2-tem\n", encoding="utf-8")
    _sdk_home(tmp_path, monkeypatch, [("java", "26.0.2-tem")])
    monkeypatch.setattr(sdkman, "available_identifiers", lambda _c: ["26.0.2-tem", "25.0.5-tem"])
    monkeypatch.setattr(upgrade, "_candidate_runs", lambda _c, i: i != "26.0.2-tem")
    calls = []

    def install(_p):
        calls.append(1)
        pinned = (tmp_path / ".sdkmanrc").read_text(encoding="utf-8").split("java=")[1].split()[0]
        (tmp_path / "sdkman" / "candidates" / "java" / pinned).mkdir(parents=True, exist_ok=True)
        return 0, "ok"

    monkeypatch.setattr(upgrade, "_run_sdk_env_install", install)
    upgrade.sdkman_env_install(tmp_path)
    text = (tmp_path / ".sdkmanrc").read_text(encoding="utf-8")
    assert "java=25.0.5-tem" in text
    assert "# sdkman-skip: java 26.0.2-tem  # installed but cannot execute" in text
    assert not (tmp_path / "sdkman" / "candidates" / "java" / "26.0.2-tem").exists()
    assert len(calls) == 2
    assert sdkman.read_skip_list(tmp_path)["java"] >= {"26.0.2-tem"}  # reason tail is not parsed as an id
    assert "installed" not in sdkman.read_skip_list(tmp_path)["java"]


def test_candidate_runs_executes_the_binary(tmp_path, monkeypatch):
    monkeypatch.setenv("SDKMAN_DIR", str(tmp_path))
    exe = tmp_path / "candidates" / "java" / "1.0-tem" / "bin" / "java"
    exe.parent.mkdir(parents=True)
    exe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    exe.chmod(0o755)
    assert _REAL_CANDIDATE_RUNS("java", "1.0-tem")
    exe.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")  # "Bad CPU type" style failure
    assert not _REAL_CANDIDATE_RUNS("java", "1.0-tem")
    assert not _REAL_CANDIDATE_RUNS("java", "missing")
    assert _REAL_CANDIDATE_RUNS("gradle", "9.7.0")  # no cheap probe -> fine


def test_native_platform_flips_rosetta_flag_on_apple_silicon(tmp_path, monkeypatch):
    monkeypatch.setenv("SDKMAN_DIR", str(tmp_path))
    config = tmp_path / "etc" / "config"
    config.parent.mkdir()
    config.write_text("a=1\nsdkman_rosetta2_compatible=true\nb=2\n", encoding="utf-8")
    monkeypatch.setattr(upgrade, "_apple_silicon", lambda: True)
    assert _REAL_ENSURE_NATIVE()
    assert config.read_text(encoding="utf-8") == "a=1\nsdkman_rosetta2_compatible=false\nb=2\n"
    assert not _REAL_ENSURE_NATIVE()  # idempotent
    monkeypatch.setattr(upgrade, "_apple_silicon", lambda: False)
    config.write_text("sdkman_rosetta2_compatible=true\n", encoding="utf-8")
    assert not _REAL_ENSURE_NATIVE()  # untouched off Apple Silicon


def test_sdk_shell_command_is_native_on_apple_silicon(monkeypatch):
    monkeypatch.setattr(upgrade, "_apple_silicon", lambda: True)
    assert upgrade._sdk_shell_command("sdk env install")[:3] == ["arch", "-arm64", "bash"]
    monkeypatch.setattr(upgrade, "_apple_silicon", lambda: False)
    assert upgrade._sdk_shell_command("sdk env install")[0] == "bash"


def test_setup_scripts_take_the_python_pin_from_python_version():
    here = Path(__file__).resolve()  # repo root (orchestrator copy) or content/ (toolkit source) is above
    for name in ("setup.sh", "setup.ps1"):
        found = [p for root in here.parents[2:5] for p in (root / name, root / "scripts" / name) if p.is_file()]
        if not found:
            pytest.skip(f"{name} not present next to this test copy")
        text = found[0].read_text(encoding="utf-8")
        assert ".python-version" in text
        assert "--python 3." not in text  # no hard-coded minor to drift from /update python


def test_update_python_no_longer_rewrites_setup_sh():
    assert "setup.sh" not in [c["file"] for c in py_mod.get_files_to_update()]
