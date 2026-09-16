"""pr_create --issue: the `Tracks #<N>` body line and the linking comment on the issue."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from modules.toolkit.repo import pr_create
from modules.toolkit.setup.properties import FamilyRepo

pytestmark = pytest.mark.repo


def _repo() -> FamilyRepo:
    return FamilyRepo(
        org="acme",
        name="widgets",
        path=Path("/x"),
        is_self=True,
        exists=True,
        default_branch="main",
        parent=None,
        status="active",
        visibility="private",
        ai=False,
        use_ci=False,
        pull_request=True,
        purpose="",
    )


def _wire(
    monkeypatch,
    calls: list,
    *,
    create_returncode: int = 0,
    create_stdout: str = "https://github.com/acme/widgets/pull/9\n",
):
    monkeypatch.setattr(pr_create, "find_current_repo", _repo)
    monkeypatch.setattr(pr_create, "get_repo_local", lambda: Path("/x"))
    monkeypatch.setattr(pr_create, "current_branch", lambda _path: "feat_x")
    monkeypatch.setattr(pr_create, "detect_base_branch", lambda _path, _branch: "origin/main")

    def _fake_run(args, **_kwargs):
        calls.append(args)
        if args[:3] == ["gh", "pr", "create"]:
            return SimpleNamespace(
                returncode=create_returncode,
                stdout=create_stdout,
                stderr="already exists" if create_returncode else "",
            )
        if args[:3] == ["gh", "issue", "comment"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if args[:3] == ["gh", "pr", "view"]:
            return SimpleNamespace(returncode=0, stdout="https://github.com/acme/widgets/pull/9\n", stderr="")
        raise AssertionError(f"unexpected subprocess call: {args}")

    monkeypatch.setattr(pr_create.subprocess, "run", _fake_run)


def test_issue_appends_tracks_line_to_body(monkeypatch):
    calls: list = []
    _wire(monkeypatch, calls)
    pr_create.main(title="t", content="c", issue=5)
    create_call = next(args for args in calls if args[:3] == ["gh", "pr", "create"])
    body = create_call[create_call.index("--body") + 1]
    assert body == "c\n\nTracks #5"


def test_issue_comments_the_pr_link_back_on_the_issue(monkeypatch):
    calls: list = []
    _wire(monkeypatch, calls)
    pr_create.main(title="t", content="c", issue=5)
    comment_call = next(args for args in calls if args[:3] == ["gh", "issue", "comment"])
    assert comment_call == [
        "gh",
        "issue",
        "comment",
        "5",
        "--repo",
        "acme/widgets",
        "--body",
        "PR: https://github.com/acme/widgets/pull/9",
    ]


def test_no_issue_leaves_body_untouched_and_skips_comment(monkeypatch):
    calls: list = []
    _wire(monkeypatch, calls)
    pr_create.main(title="t", content="c")
    create_call = next(args for args in calls if args[:3] == ["gh", "pr", "create"])
    assert create_call[create_call.index("--body") + 1] == "c"
    assert not any(args[:3] == ["gh", "issue", "comment"] for args in calls)


def test_issue_still_linked_when_pr_already_exists(monkeypatch):
    calls: list = []
    _wire(monkeypatch, calls, create_returncode=1, create_stdout="")
    pr_create.main(title="t", content="c", issue=7)
    comment_call = next(args for args in calls if args[:3] == ["gh", "issue", "comment"])
    assert comment_call[3] == "7"
    assert comment_call[-1] == "PR: https://github.com/acme/widgets/pull/9"


def test_link_issue_failure_does_not_raise(monkeypatch, capsys):
    calls: list = []
    _wire(monkeypatch, calls)

    def _fake_run(args, **_kwargs):
        calls.append(args)
        if args[:3] == ["gh", "pr", "create"]:
            return SimpleNamespace(returncode=0, stdout="https://github.com/acme/widgets/pull/9\n", stderr="")
        if args[:3] == ["gh", "issue", "comment"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="not found")
        raise AssertionError(f"unexpected subprocess call: {args}")

    monkeypatch.setattr(pr_create.subprocess, "run", _fake_run)
    pr_create.main(title="t", content="c", issue=5)  # must not raise
    assert "couldn't comment on acme/widgets#5" in capsys.readouterr().out
