"""modules.toolkit.repo.cleanup — the phase-2 local-trash sweep."""

import subprocess

import pytest
from modules.toolkit.repo import cleanup

pytestmark = pytest.mark.repo


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "modules" / "live").mkdir(parents=True)
    (tmp_path / "modules" / "live" / "mod.py").write_text("x\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_live.py").write_text("def test(): ...\n")
    (tmp_path / "topics" / "notes").mkdir(parents=True)
    (tmp_path / "topics" / "notes" / "a.md").write_text("y\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")

    (tmp_path / "modules" / "orphan" / "__pycache__").mkdir(parents=True)
    (tmp_path / "modules" / "orphan" / "__pycache__" / "x.pyc").write_text("z")
    (tmp_path / "modules" / "live" / "__pycache__").mkdir()
    (tmp_path / "modules" / "live" / "__pycache__" / "m.pyc").write_text("z")
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "v.json").write_text("{}")
    (tmp_path / "ai.egg-info").mkdir()
    (tmp_path / "topics" / "notes" / "__pycache__").mkdir()  # under topics/ — must be left alone
    return tmp_path


def test_find_orphan_dirs_only_flags_pure_residue(repo):
    orphans, suspects = cleanup._find_orphan_dirs(repo)
    assert {p.name for p in orphans} == {"orphan"}
    assert suspects == []


def test_untracked_new_work_is_a_suspect_not_an_orphan(repo):
    # a brand-new, not-yet-added test dir — zero tracked files, but real source
    (repo / "tests" / "new_feature").mkdir(parents=True)
    (repo / "tests" / "new_feature" / "test_it.py").write_text("def test(): ...\n")
    orphans, suspects = cleanup._find_orphan_dirs(repo)
    assert {p.name for p in orphans} == {"orphan"}
    assert {p.name for p in suspects} == {"new_feature"}


def test_find_caches_skips_venv_and_topics(repo):
    (repo / ".venv" / "__pycache__").mkdir(parents=True)
    found = {p.relative_to(repo).as_posix() for p in cleanup._find_caches(repo)}
    assert {"modules/live/__pycache__", ".pytest_cache", "ai.egg-info"} <= found
    assert not any(c.startswith((".venv", "topics")) for c in found)


def test_sweep_removes_trash_keeps_tracked_topics_and_new_work(repo, monkeypatch):
    (repo / "tests" / "new_feature").mkdir(parents=True)
    (repo / "tests" / "new_feature" / "test_it.py").write_text("def test(): ...\n")
    monkeypatch.setenv("AUTO_CONFIRM", "1")
    cleanup._sweep_trash(repo)
    assert (repo / "modules" / "live" / "mod.py").exists()
    assert (repo / "topics" / "notes" / "a.md").exists()
    assert (repo / "topics" / "notes" / "__pycache__").exists()
    assert (repo / "tests" / "new_feature" / "test_it.py").exists()  # suspect — untouched
    assert not (repo / "modules" / "orphan").exists()
    assert not (repo / ".pytest_cache").exists()
    assert not (repo / "ai.egg-info").exists()
    assert not (repo / "modules" / "live" / "__pycache__").exists()


@pytest.fixture
def gitkeep_repo(repo):
    """`repo` plus a spread of tracked .gitkeep placeholders:
    - modules/live/.gitkeep  → dir already has mod.py                (redundant)
    - assets/.gitkeep        → dir also has logo.svg                 (redundant)
    - data/.gitkeep          → content lives only in data/sub/x.txt  (redundant — subdir counts)
    - modules/hollow/.gitkeep → the only tracked file in its dir     (still needed)
    """
    (repo / "modules" / "live" / ".gitkeep").write_text("")
    (repo / "assets").mkdir()
    (repo / "assets" / ".gitkeep").write_text("")
    (repo / "assets" / "logo.svg").write_text("<svg/>\n")
    (repo / "data" / "sub").mkdir(parents=True)
    (repo / "data" / ".gitkeep").write_text("")
    (repo / "data" / "sub" / "x.txt").write_text("x\n")
    (repo / "modules" / "hollow").mkdir()
    (repo / "modules" / "hollow" / ".gitkeep").write_text("")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "gitkeeps")
    return repo


def test_find_redundant_gitkeeps_only_flags_populated_dirs(gitkeep_repo):
    found = {p.relative_to(gitkeep_repo).as_posix() for p in cleanup._find_redundant_gitkeeps(gitkeep_repo)}
    assert found == {"modules/live/.gitkeep", "assets/.gitkeep", "data/.gitkeep"}


def test_untracked_gitkeep_is_ignored(gitkeep_repo):
    (gitkeep_repo / "scratch").mkdir()
    (gitkeep_repo / "scratch" / ".gitkeep").write_text("")  # never added
    (gitkeep_repo / "scratch" / "note.txt").write_text("hi\n")
    found = {p.relative_to(gitkeep_repo).as_posix() for p in cleanup._find_redundant_gitkeeps(gitkeep_repo)}
    assert "scratch/.gitkeep" not in found


def test_remove_redundant_gitkeeps_stages_the_deletion(gitkeep_repo, monkeypatch):
    monkeypatch.setenv("AUTO_CONFIRM", "1")
    cleanup._remove_redundant_gitkeeps(gitkeep_repo)

    assert not (gitkeep_repo / "modules" / "live" / ".gitkeep").exists()
    assert not (gitkeep_repo / "assets" / ".gitkeep").exists()
    assert (gitkeep_repo / "modules" / "hollow" / ".gitkeep").exists()  # still needed

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        cwd=gitkeep_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "D\tassets/.gitkeep" in staged
    assert "D\tmodules/live/.gitkeep" in staged
