"""modules.toolkit.backlog.list — the grouped-Markdown-table output and `--all` aggregation."""

import json
import subprocess
from pathlib import Path

import pytest
from modules.toolkit.backlog import list as backlog_list
from modules.toolkit.setup.properties import FamilyRepo

pytestmark = pytest.mark.backlog


def _repo(name, *, org="fireballenterprise"):
    return FamilyRepo(
        org=org,
        name=name,
        path=Path("/nonexistent") / name,
        is_self=False,
        exists=False,
        default_branch="main",
        parent=None,
        status="active",
        visibility="private",
        ai=False,
        use_ci=False,
        pull_request=False,
        purpose="",
    )


_FAMILY = [_repo("fireball_sidecar_vscode"), _repo("fireball_ai_toolkit"), _repo("fireball_orchestrator")]

#: fuzzy `--repo` token → the repo it resolves to.
_RESOLVE = {
    "toolkit": "fireball_ai_toolkit",
    "orchestrator": "fireball_orchestrator",
    "": "fireball_ai_toolkit",
}


def _issue(number, title, labels, repo):
    return {
        "number": number,
        "title": title,
        "url": f"https://github.com/fireballenterprise/{repo}/issues/{number}",
        "labels": [{"name": name} for name in labels],
    }


#: `org/name` → that repo's `gh issue list --json` payload.
_ISSUES = {
    "fireballenterprise/fireball_sidecar_vscode": [
        _issue(12, "blank chat panel on a piped | title", ["Sidecar VSCode", "UI"], "fireball_sidecar_vscode"),
    ],
    "fireballenterprise/fireball_ai_toolkit": [
        _issue(
            52,
            "backlog list --all should aggregate every family repo into one grouped view",
            ["AI Toolkit", "backlog"],
            "fireball_ai_toolkit",
        ),
    ],
    "fireballenterprise/fireball_orchestrator": [],
}


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    monkeypatch.setattr(backlog_list, "get_family_repos", lambda **_kw: list(_FAMILY))
    monkeypatch.setattr(backlog_list, "resolve_repo_or_current", lambda token: _repo(_RESOLVE[token]))

    def fake_gh(args, *, repo=None, check=True):
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(_ISSUES.get(repo, [])), stderr="")

    monkeypatch.setattr(backlog_list, "gh", fake_gh)


def test_single_repo_renders_a_heading_and_table(capsys):
    backlog_list.main(repo="toolkit")
    out = capsys.readouterr().out
    assert "### fireball_ai_toolkit · 1" in out
    assert "| # | Title | Labels |" in out
    assert "| [#52](https://github.com/fireballenterprise/fireball_ai_toolkit/issues/52) |" in out
    # area label stripped, finer label kept
    assert "| backlog |" in out
    assert "AI Toolkit" not in out


def test_title_is_truncated_with_an_ellipsis(capsys):
    backlog_list.main(repo="toolkit")
    out = capsys.readouterr().out
    assert "…" in out
    assert "aggregate every family repo into one grouped view" not in out


def test_pipe_in_a_title_is_escaped(capsys):
    backlog_list.main(all_repos=True)
    out = capsys.readouterr().out
    assert "piped \\| title" in out


def test_single_repo_empty_state(capsys):
    backlog_list.main(repo="orchestrator")
    out = capsys.readouterr().out
    assert "*No open issues in fireball_orchestrator.*" in out
    assert out.strip().startswith("<!--sidecar:verbatim-->")
    assert out.strip().endswith("<!--sidecar:/verbatim-->")


def test_human_output_is_verbatim_fenced(capsys):
    backlog_list.main(all_repos=True)
    out = capsys.readouterr().out.strip()
    assert out.startswith("<!--sidecar:verbatim-->\n")
    assert out.endswith("\n<!--sidecar:/verbatim-->")
    # exactly one fenced block wrapping the whole answer
    assert out.count("<!--sidecar:verbatim-->") == 1


def test_json_output_is_never_fenced(capsys):
    backlog_list.main(all_repos=True, as_json=True)
    assert "sidecar:verbatim" not in capsys.readouterr().out


def test_all_groups_by_repo_and_collapses_empty(capsys):
    backlog_list.main(all_repos=True)
    out = capsys.readouterr().out
    assert "## Open issues — family" in out
    assert "**2 open across 3 repos**" in out
    assert "### fireball_sidecar_vscode · 1" in out
    assert "### fireball_ai_toolkit · 1" in out
    assert "fireball_orchestrator" not in out
    assert "*1 other repo: none*" in out


def test_all_empty_prints_the_all_empty_line(capsys, monkeypatch):
    monkeypatch.setattr(backlog_list, "_issues", lambda *_a, **_k: [])
    backlog_list.main(all_repos=True)
    out = capsys.readouterr().out
    assert "**0 open across 3 repos**" in out
    assert "*No open issues in any family repo.*" in out


def test_filter_note_shows_in_the_heading(capsys):
    backlog_list.main(repo="toolkit", issue_type="bug", mine=True)
    assert "*filtered: type:bug, assigned to you*" in capsys.readouterr().out


def test_all_json_tags_each_row_with_repo(capsys):
    backlog_list.main(all_repos=True, as_json=True)
    payload = json.loads(capsys.readouterr().out)
    assert {row["repo"] for row in payload} == {
        "fireballenterprise/fireball_sidecar_vscode",
        "fireballenterprise/fireball_ai_toolkit",
    }
    assert {row["number"] for row in payload} == {12, 52}


def test_single_repo_json_is_the_raw_array(capsys):
    backlog_list.main(repo="toolkit", as_json=True)
    payload = json.loads(capsys.readouterr().out)
    assert [row["number"] for row in payload] == [52]
    assert "repo" not in payload[0]


def test_all_and_repo_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        backlog_list.main(all_repos=True, repo="toolkit")


def test_scope_requires_all():
    with pytest.raises(SystemExit):
        backlog_list.main(scope="ai")


def test_scope_must_be_known():
    with pytest.raises(SystemExit):
        backlog_list.main(all_repos=True, scope="bogus")
