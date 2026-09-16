"""modules.toolkit.common.toolchains — marker-file → toolchain / capability detection."""

import pytest
from modules.toolkit.common import toolchains

pytestmark = pytest.mark.common


def test_empty_dir_detects_nothing(tmp_path):
    assert toolchains.detect(tmp_path) == set()
    assert toolchains.capabilities(tmp_path) == set()


def test_python_repo(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    tokens = toolchains.detect(tmp_path)
    assert "python" in tokens
    caps = toolchains.capabilities(tmp_path)
    assert {"check:libs", "check:python", "style:ruff", "style:pylint", "unit:pytest"} <= caps


def test_sdkmanrc_gives_sdkman_and_candidates(tmp_path):
    (tmp_path / ".sdkmanrc").write_text("java=26.0.2-tem\ngradle=9.7.0\n")
    tokens = toolchains.detect(tmp_path)
    assert {"sdkman", "java", "gradle"} <= tokens
    assert "check:sdkman" in toolchains.capabilities(tmp_path)
    assert "check:python" not in toolchains.capabilities(tmp_path)


def test_workflows_marker(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("on: push\n")
    assert "workflows" in toolchains.detect(tmp_path)
    assert {"check:workflows", "style:actionlint"} <= toolchains.capabilities(tmp_path)


def test_kotlin_needs_gradle_and_real_sources(tmp_path):
    (tmp_path / "build.gradle.kts").write_text("plugins {}\n")
    assert "gradle" in toolchains.detect(tmp_path)
    assert "kotlin" not in toolchains.detect(tmp_path)  # no .kt sources yet
    src = tmp_path / "app" / "src" / "main"
    src.mkdir(parents=True)
    (src / "Main.kt").write_text("fun main() {}\n")
    assert "kotlin" in toolchains.detect(tmp_path)
    assert {"style:ktlint", "style:detekt", "unit:gradle"} <= toolchains.capabilities(tmp_path)


def test_agp_enables_android_lint(tmp_path):
    (tmp_path / "build.gradle.kts").write_text('plugins { id("com.android.application") }\n')
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "A.kt").write_text("class A\n")
    assert "agp" in toolchains.detect(tmp_path)
    assert "style:android-lint" in toolchains.capabilities(tmp_path)
