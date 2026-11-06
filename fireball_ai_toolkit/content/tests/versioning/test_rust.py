"""modules.fireball_ai_toolkit.versioning.rust — pin parsing, latest-stable decision, offline safety, repo-local
install (network and subprocess mocked), and the toolchain/route/upgrade wiring."""

import subprocess
from datetime import date

import pytest
from modules.fireball_ai_toolkit.common import toolchains
from modules.fireball_ai_toolkit.versioning import check, route, rust, upgrade

pytestmark = pytest.mark.versioning

MANIFEST = {"date": "2026-10-15", "pkg": {"rust": {"version": "1.99.1 (58cf8f9c3 2026-10-13)"}}}


def _pin(tmp_path, channel="1.99.1"):
    (tmp_path / "rust-toolchain.toml").write_text(
        f'# comment\n[toolchain]\nchannel = "{channel}"\ncomponents = ["clippy", "rustfmt"]\nprofile = "minimal"\n',
        encoding="utf-8",
    )
    return tmp_path


def test_read_pin_exact_only(tmp_path):
    assert rust.read_pin(_pin(tmp_path)) == "1.99.1"
    assert rust.read_pin(_pin(tmp_path, "stable")) is None
    assert rust.read_pin(tmp_path / "missing") is None


def test_write_pin_keeps_comments_and_other_keys(tmp_path):
    _pin(tmp_path)
    rust.write_pin(tmp_path, "2.0.0")
    text = (tmp_path / "rust-toolchain.toml").read_text(encoding="utf-8")
    assert 'channel = "2.0.0"' in text and "# comment" in text and 'profile = "minimal"' in text
    assert rust.read_components(tmp_path) == ["clippy", "rustfmt"]


def test_latest_stable_parses_manifest():
    assert rust.latest_stable(MANIFEST) == ("1.99.1", date(2026, 10, 15))
    assert rust.latest_stable({}) is None


def test_decide_respects_age_and_order():
    released = date(2026, 10, 15)
    assert rust.decide("1.98.0", "1.99.1", released, today=date(2026, 11, 6)) == "1.99.1"
    assert rust.decide("1.98.0", "1.99.1", released, today=date(2026, 10, 20)) is None  # too young
    assert rust.decide("1.99.1", "1.99.1", released, today=date(2026, 11, 6)) is None
    assert rust.decide("1.100.0", "1.99.1", released, today=date(2026, 11, 6)) is None  # numeric, not lexical


def test_fetch_manifest_offline_is_none(monkeypatch):
    def boom(*_a, **_k):
        raise rust.urllib.error.URLError("offline")

    monkeypatch.setattr(rust.urllib.request, "urlopen", boom)
    assert rust.fetch_manifest() is None


def _run_main(monkeypatch, root, **kwargs):
    monkeypatch.setattr(rust, "get_repo_local", lambda: root)
    try:
        rust.main(**kwargs)
    except SystemExit as exc:
        return exc.code
    return 0


def test_main_exits_3_without_pin(monkeypatch, tmp_path):
    assert _run_main(monkeypatch, tmp_path, dry_run=True, no_confirm=True) == 3


def test_main_exits_3_in_a_cargo_workspace(monkeypatch, tmp_path):
    _pin(tmp_path)
    (tmp_path / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
    assert _run_main(monkeypatch, tmp_path, dry_run=False, no_confirm=True) == 3
    assert rust.read_pin(tmp_path) == "1.99.1"


def test_main_offline_warns_and_exits_3(monkeypatch, tmp_path):
    _pin(tmp_path)
    monkeypatch.setattr(rust, "fetch_manifest", lambda: None)
    assert _run_main(monkeypatch, tmp_path, dry_run=False, no_confirm=True) == 3


def test_main_dry_run_and_apply(monkeypatch, tmp_path):
    _pin(tmp_path, "1.98.0")
    monkeypatch.setattr(rust, "fetch_manifest", lambda: MANIFEST)
    monkeypatch.setattr(rust, "decide", lambda current, latest, released, today=None: latest)
    assert _run_main(monkeypatch, tmp_path, dry_run=True, no_confirm=True) == 0
    assert rust.read_pin(tmp_path) == "1.98.0"
    assert _run_main(monkeypatch, tmp_path, dry_run=False, no_confirm=True) == 0
    assert rust.read_pin(tmp_path) == "1.99.1"


def test_local_env_is_repo_local(tmp_path):
    env = rust.local_env(tmp_path, toolchain="1.99.1")
    assert env["RUSTUP_HOME"] == str(tmp_path / ".rust" / "rustup")
    assert env["CARGO_HOME"] == str(tmp_path / ".rust" / "cargo")
    assert env["PATH"].startswith(str(tmp_path / ".rust" / "cargo" / "bin"))
    assert env["RUSTUP_TOOLCHAIN"] == "1.99.1"


def _fake_install(tmp_path, *names):
    bin_dir = tmp_path / ".rust" / "cargo" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / f"rustup{rust.EXE}").write_text("", encoding="utf-8")
    for name in names:
        (tmp_path / ".rust" / "rustup" / "toolchains" / name).mkdir(parents=True)


def test_is_installed_and_superseded(tmp_path):
    _fake_install(tmp_path, "1.98.0-aarch64-apple-darwin", "1.99.1-aarch64-apple-darwin")
    assert rust.is_installed(tmp_path, "1.99.1")
    assert not rust.is_installed(tmp_path, "2.0.0")
    assert rust.superseded(tmp_path, "1.99.1") == ["1.98.0-aarch64-apple-darwin"]


def test_install_pinned_installs_defaults_and_uninstalls_old(monkeypatch, tmp_path):
    _pin(tmp_path)
    _fake_install(tmp_path, "1.98.0-aarch64-apple-darwin")
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd[1:], kwargs["env"]["RUSTUP_HOME"]))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(rust.subprocess, "run", fake_run)
    assert rust.install_pinned(tmp_path, "1.99.1")
    verbs = [c for c, _ in calls]
    assert [
        "toolchain",
        "install",
        "1.99.1",
        "--profile",
        "minimal",
        "-c",
        "clippy",
        "-c",
        "rustfmt",
        "--no-self-update",
    ] in verbs
    assert ["default", "1.99.1"] in verbs
    assert ["toolchain", "uninstall", "1.98.0-aarch64-apple-darwin"] in verbs
    assert {home for _, home in calls} == {str(tmp_path / ".rust" / "rustup")}


def test_install_pinned_stops_when_bootstrap_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(rust, "bootstrap_rustup", lambda _p: False)
    assert rust.install_pinned(tmp_path, "1.99.1") is False


def test_host_triple_shape():
    assert rust.host_triple().count("-") >= 2


def test_owns_rust_and_detect(tmp_path):
    assert not toolchains.owns_rust(tmp_path)
    _pin(tmp_path)
    assert toolchains.owns_rust(tmp_path)
    assert "rust_pin" in toolchains.detect(tmp_path)
    assert "check:rust" in toolchains.capabilities(tmp_path)
    (tmp_path / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
    assert not toolchains.owns_rust(tmp_path)
    assert "rust_pin" not in toolchains.detect(tmp_path)


def test_check_runs_rust_for_the_owner(monkeypatch, tmp_path):
    _pin(tmp_path)
    ran = []
    monkeypatch.setattr(check, "find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(check, "_run_one", lambda name, flags: ran.append(name) or 0)
    monkeypatch.setattr("sys.argv", ["check"])
    check.main()
    assert ran == ["rust"]


def test_route_accepts_rust_subarg():
    assert "rust" in route._VERBS["check"][1]
    assert "rust" in route._VERBS["upgrade"][1]


def _run_upgrade(monkeypatch, root, installed):
    monkeypatch.setattr(upgrade, "get_repo_local", lambda: root)
    monkeypatch.setattr(upgrade, "rust_install", lambda repo, version: installed.append(version))
    try:
        upgrade.main(only="rust", sync_only=False, no_confirm=True)
    except SystemExit as exc:
        return exc.code
    return 0


def test_upgrade_installs_the_pin_when_missing(monkeypatch, tmp_path):
    _pin(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    installed = []
    _run_upgrade(monkeypatch, tmp_path, installed)
    assert installed == ["1.99.1"]


def test_upgrade_skips_when_pin_already_installed(monkeypatch, tmp_path):
    _pin(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    _fake_install(tmp_path, "1.99.1-aarch64-apple-darwin")
    installed = []
    assert _run_upgrade(monkeypatch, tmp_path, installed) == 0
    assert installed == []


def test_upgrade_ignores_a_cargo_workspace(monkeypatch, tmp_path):
    _pin(tmp_path)
    (tmp_path / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
    installed = []
    _run_upgrade(monkeypatch, tmp_path, installed)
    assert installed == []
