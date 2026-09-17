"""apply / check / sync against a throwaway git repo."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from fireball_ai_toolkit import sync
from fireball_ai_toolkit.apply import DirtySharedError, apply
from fireball_ai_toolkit.check import DriftError, check

pytestmark = pytest.mark.ai_toolkit


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "README.md").write_text("x\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def test_apply_clobbers_shared_and_renders(repo: Path):
    result = apply(repo)
    assert result.by_count > 20
    assert (repo / ".fireball_ai_toolkit" / "toolkit" / "commands").is_dir()
    assert (repo / ".fireball_ai_toolkit" / "toolkit" / "instructions").is_dir()
    assert (repo / "AGENTS.md").exists()
    assert (repo / ".claude" / "commands").is_dir()


def test_download_alias_still_works(repo: Path):
    from fireball_ai_toolkit.apply import download

    assert download is apply


def test_cli_apply_renders_and_reports(repo: Path, capsys: pytest.CaptureFixture[str]):
    from fireball_ai_toolkit.cli import main

    assert main(["--repo", str(repo), "apply"]) == 0
    assert "Rendered" in capsys.readouterr().out
    assert (repo / "AGENTS.md").exists()


def test_cli_sync_stops_on_dirty_shared_without_yes(repo: Path):
    from fireball_ai_toolkit.cli import main

    main(["--repo", str(repo), "apply"])
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "generated")
    (repo / ".fireball_ai_toolkit" / "toolkit" / "commands" / "fix.md").write_text("hand edit\n")
    assert main(["--repo", str(repo), "sync"]) == 2  # refuses to clobber a local edit
    assert main(["--repo", str(repo), "sync", "--yes"]) == 0  # --yes discards it


def test_apply_clobbers_the_shared_python_and_scripts(repo: Path):
    apply(repo)
    assert (repo / "modules" / "toolkit" / "setup" / "properties.py").is_file()
    assert (repo / "tasks" / "toolkit" / "main.py").is_file()
    assert (repo / "tasks" / "toolkit" / "versioning.py").is_file()
    assert (repo / "tests" / "toolkit").is_dir()
    setup = repo / "setup.sh"
    assert setup.is_file() and setup.stat().st_mode & 0o111  # executable
    assert (repo / "setup.ps1").is_file()


def test_check_flags_a_tampered_shared_module(repo: Path):
    apply(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "generated")
    (repo / "modules" / "toolkit" / "setup" / "properties.py").write_text("tampered\n")
    with pytest.raises(DriftError, match="modules/toolkit/setup/properties.py"):
        check(repo)


def test_check_passes_immediately_after_apply(repo: Path):
    apply(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "generated")
    check(repo)  # no raise


def test_check_raises_when_a_generated_file_is_edited(repo: Path):
    apply(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "generated")
    (repo / "AGENTS.md").write_text("hand-edited\n")
    with pytest.raises(DriftError, match="AGENTS.md"):
        check(repo)


def test_check_raises_when_shared_is_missing(repo: Path):
    with pytest.raises(DriftError, match=".fireball_ai_toolkit/toolkit"):
        check(repo)


def test_apply_allows_untracked_shared(repo: Path):
    apply(repo)  # creates an untracked _shared/
    apply(repo)  # a second run before committing must not trip the dirty guard


def test_apply_refuses_dirty_shared(repo: Path):
    apply(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "generated")
    (repo / ".fireball_ai_toolkit" / "toolkit" / "commands" / "fix.md").write_text("tampered\n")
    with pytest.raises(DirtySharedError):
        apply(repo)
    apply(repo, force=True)  # force overrides


def test_sync_inspect_reports_clean_then_dirty(repo: Path):
    apply(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "generated")
    assert sync.inspect(repo).dirty is False

    (repo / ".fireball_ai_toolkit" / "toolkit" / "commands" / "fix.md").write_text("tampered\n")
    plan = sync.inspect(repo)
    assert plan.dirty is True
    assert "fix.md" in plan.shared_diff


def test_vendor_subset_skips_python_trees(repo: Path):
    (repo / ".ai-toolkit.yml").write_text("vendor:\n  - ai\n  - scripts\n")
    apply(repo)
    assert (repo / ".fireball_ai_toolkit" / "toolkit" / "commands").is_dir()  # ai vendored
    assert (repo / "setup.sh").is_file()  # scripts vendored
    assert not (repo / "modules" / "toolkit").exists()  # modules NOT vendored
    assert not (repo / "tasks" / "toolkit").exists()
    assert not (repo / "tests" / "toolkit").exists()

    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "generated")
    check(repo)  # no raise — check ignores the un-vendored trees

    # a hand-edited generated file is still caught
    (repo / "AGENTS.md").write_text("hand-edited\n")
    with pytest.raises(DriftError, match="AGENTS.md"):
        check(repo)


def test_vendor_subset_without_ai_skips_render(repo: Path):
    (repo / ".ai-toolkit.yml").write_text("vendor: [scripts]\n")
    result = apply(repo)
    assert result.by_count == 0
    assert (repo / "setup.sh").is_file()
    assert not (repo / ".fireball_ai_toolkit" / "toolkit").exists()
    assert not (repo / "AGENTS.md").exists()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "generated")
    check(repo)  # no raise


def test_vendor_config_rejects_unknown_keys(repo: Path):
    (repo / ".ai-toolkit.yml").write_text("vendor: [ai, bogus]\n")
    with pytest.raises(ValueError, match="bogus"):
        apply(repo)
