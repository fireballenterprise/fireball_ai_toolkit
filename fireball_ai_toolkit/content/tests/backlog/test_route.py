"""modules.toolkit.backlog.route — the thin `/backlog <subcommand>` dispatcher."""

import pytest
from modules.toolkit.backlog import route as backlog_route

pytestmark = pytest.mark.backlog


class _Result:
    returncode = 0


@pytest.fixture
def dispatched(monkeypatch, tmp_path):
    """Capture the command `route.main()` would run instead of spawning it."""
    calls = []

    def _fake_run(command, **kwargs):
        calls.append(command)
        return _Result()

    monkeypatch.setattr(backlog_route.subprocess, "run", _fake_run)
    monkeypatch.setattr(backlog_route, "find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(backlog_route, "build_env", lambda _root: {})
    return calls


def _run(monkeypatch, argstring):
    monkeypatch.setattr("sys.argv", ["backlog", argstring] if argstring is not None else ["backlog"])
    return backlog_route.main()


def _tail(command):
    """The `-m modules.toolkit.backlog.<sub> ...` portion of the spawned command."""
    return command[command.index("-m") + 1 :]


def test_bare_invocation_defaults_to_list_all(monkeypatch, dispatched):
    assert _run(monkeypatch, "") == 0
    assert _tail(dispatched[0]) == ["modules.toolkit.backlog.list", "--all"]


def test_no_argv_at_all_defaults_to_list_all(monkeypatch, dispatched):
    assert _run(monkeypatch, None) == 0
    assert _tail(dispatched[0]) == ["modules.toolkit.backlog.list", "--all"]


def test_unknown_subcommand_still_errors(monkeypatch, dispatched, capsys):
    assert _run(monkeypatch, "xyz") == 1
    assert not dispatched
    assert "usage: backlog {add|close|comment|list|start|view}" in capsys.readouterr().err


def test_known_subcommand_passes_through(monkeypatch, dispatched):
    assert _run(monkeypatch, "list --repo toolkit") == 0
    assert _tail(dispatched[0]) == ["modules.toolkit.backlog.list", "--repo", "toolkit"]


def test_add_bug_shorthand_expands_to_type_flag(monkeypatch, dispatched):
    assert _run(monkeypatch, 'add bug --repo toolkit --title "x"') == 0
    assert _tail(dispatched[0]) == [
        "modules.toolkit.backlog.add",
        "--type",
        "bug",
        "--repo",
        "toolkit",
        "--title",
        "x",
    ]
