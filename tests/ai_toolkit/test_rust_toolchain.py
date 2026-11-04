"""Rust repos: a `Cargo.toml` turns on rustfmt, clippy, cargo-deny (only with a `deny.toml`) and cargo test."""

from fireball_ai_toolkit.content.modules.common import toolchains
from fireball_ai_toolkit.content.modules.tests import cargo_deny, cargo_test, clippy, rustfmt


def test_a_cargo_workspace_is_a_rust_repo(tmp_path):
    (tmp_path / "Cargo.toml").write_text("[workspace]\nmembers = []\n", encoding="utf-8")
    assert "rust" in toolchains.detect(tmp_path)
    assert {"style:rustfmt", "style:clippy", "style:cargo-deny", "unit:cargo"} <= toolchains.capabilities(tmp_path)
    assert rustfmt.applies(tmp_path) and clippy.applies(tmp_path) and cargo_test.applies(tmp_path)


def test_cargo_deny_runs_only_with_a_deny_toml(tmp_path):
    (tmp_path / "Cargo.toml").write_text("[workspace]\nmembers = []\n", encoding="utf-8")
    assert not cargo_deny.applies(tmp_path)
    (tmp_path / "deny.toml").write_text("[licenses]\nallow = []\n", encoding="utf-8")
    assert cargo_deny.applies(tmp_path)


def test_a_repo_without_cargo_runs_no_rust_tools(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    assert "rust" not in toolchains.detect(tmp_path)
    assert not any(module.applies(tmp_path) for module in (rustfmt, clippy, cargo_deny, cargo_test))


def test_cargo_target_is_never_walked(tmp_path):
    # A Gradle build marker plus a `.kt` file only under `target/` (Cargo's build output) is not a Kotlin repo.
    (tmp_path / "settings.gradle.kts").write_text("", encoding="utf-8")
    (tmp_path / "target" / "debug").mkdir(parents=True)
    (tmp_path / "target" / "debug" / "app.kt").write_text("", encoding="utf-8")
    assert "kotlin" not in toolchains.detect(tmp_path)
