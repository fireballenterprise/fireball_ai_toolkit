"""`tests.common.run` runs cargo with the orchestrator's pinned, repo-local toolchain and never silently skips a Rust repo."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.ai_toolkit

_COMMON = Path(__file__).resolve().parents[2] / "fireball_ai_toolkit" / "content" / "modules" / "tests" / "common.py"


def _load():
    spec = importlib.util.spec_from_file_location("runner_common", _COMMON)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look the module up by name
    spec.loader.exec_module(module)
    return module


def _checkout(tmp_path: Path, *, installed: bool) -> Path:
    root = tmp_path / "orch"
    (root / "modules" / "x" / "tests").mkdir(parents=True)
    (root / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "1.99.1"\nprofile = "minimal"\n')
    if installed:
        (root / ".rust" / "cargo" / "bin").mkdir(parents=True)
    return root


def test_pinned_env_points_at_the_repo_local_toolchain(tmp_path):
    common = _load()
    root = _checkout(tmp_path, installed=True)
    env = common.pinned_rust_env(root / "modules" / "x" / "tests" / "common.py")
    assert env["RUSTUP_TOOLCHAIN"] == "1.99.1"
    assert env["CARGO_HOME"] == str(root / ".rust" / "cargo")
    assert env["RUSTUP_HOME"] == str(root / ".rust" / "rustup")
    assert env["PATH"].startswith(str(root / ".rust" / "cargo" / "bin"))


def test_no_pin_or_no_install_means_plain_cargo(tmp_path):
    common = _load()
    root = _checkout(tmp_path, installed=False)
    assert common.pinned_rust_env(root / "modules" / "x" / "tests" / "common.py") == {}


def test_missing_cargo_fails_loudly_but_other_tools_still_skip(tmp_path, monkeypatch):
    common = _load()
    monkeypatch.setenv("PATH", str(tmp_path))  # nothing on PATH
    monkeypatch.setattr(common, "pinned_rust_env", lambda *a, **k: {})
    cargo = common.run("clippy", ["cargo", "clippy"], tmp_path)
    assert cargo.status == common.OFFENSES and "invoke setup" in cargo.note
    other = common.run("ruff", ["ruff", "check"], tmp_path)
    assert other.status == common.SKIPPED
