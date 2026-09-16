"""pr_create refuses to open a PR in a pull_request: false repo."""

from pathlib import Path

import pytest
from modules.toolkit.repo import pr_create
from modules.toolkit.setup.properties import FamilyRepo

pytestmark = pytest.mark.repo


def _repo(pull_request: bool) -> FamilyRepo:
    return FamilyRepo(
        org="o",
        name="r",
        path=Path("/x"),
        is_self=True,
        exists=True,
        default_branch="main",
        parent=None,
        status="active",
        visibility="private",
        ai=False,
        use_ci=False,
        pull_request=pull_request,
        purpose="",
    )


def test_refuses_when_pull_request_false(monkeypatch):
    monkeypatch.setattr(pr_create, "find_current_repo", lambda: _repo(False))
    with pytest.raises(SystemExit):
        pr_create.main(title="t", content="c")


def test_proceeds_past_the_guard_when_pull_request_true(monkeypatch):
    monkeypatch.setattr(pr_create, "find_current_repo", lambda: _repo(True))
    # gets past the flag guard, then fails the empty-content check (SystemExit too, different reason)
    with pytest.raises(SystemExit):
        pr_create.main(title="t", content="  ")
