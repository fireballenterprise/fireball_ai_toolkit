"""modules.toolkit.repo.route — usage, family-token routing, list/apply, module dispatch."""

import pytest
from modules.toolkit.repo import route

pytestmark = pytest.mark.repo


def _main(monkeypatch, argstr: str) -> int:
    monkeypatch.setattr("sys.argv", ["route", argstr])
    return route.main()


def _main_argv(monkeypatch, *argv: str) -> int:
    """Call `route` with separate argv entries — `route pull all`, not `route "pull all"`."""
    monkeypatch.setattr("sys.argv", ["route", *argv])
    return route.main()


def test_no_args_prints_usage(monkeypatch, capsys):
    assert _main(monkeypatch, "") == 0
    assert "repo and repo-family operations" in capsys.readouterr().out


def test_unknown_subcommand_errors_with_usage(monkeypatch, capsys):
    assert _main(monkeypatch, "frobnicate") == 1
    captured = capsys.readouterr()
    assert "Unknown repo subcommand" in captured.err


def test_apply_prints_pointer(monkeypatch, capsys):
    assert _main(monkeypatch, "apply refactor the widget") == 0
    assert "agent-driven" in capsys.readouterr().out


def test_list_delegates_to_family(monkeypatch):
    calls = []
    monkeypatch.setattr(route.family, "print_map", lambda: calls.append("map") or 0)
    assert _main(monkeypatch, "list") == 0
    assert calls == ["map"]


def test_self_delegates_to_family(monkeypatch):
    calls = []
    monkeypatch.setattr(route.family, "print_self", lambda: calls.append("self") or 0)
    assert _main(monkeypatch, "self") == 0
    assert calls == ["self"]


@pytest.mark.parametrize(
    ("arg", "verb", "scope"),
    [("pull all", "pull", None), ("push ai", "push", "ai"), ("cleanup dev_prd", "cleanup", "dev_prd")],
)
def test_scope_token_routes_to_family(monkeypatch, arg, verb, scope):
    seen = {}
    monkeypatch.setattr(
        route.family,
        "run_family",
        lambda v, *, assume_yes, scope: seen.update(verb=v, yes=assume_yes, scope=scope) or 0,
    )
    assert _main(monkeypatch, arg) == 0
    assert seen == {"verb": verb, "yes": False, "scope": scope}


def test_all_with_yes_flag(monkeypatch):
    seen = {}
    monkeypatch.setattr(route.family, "run_family", lambda v, *, assume_yes, scope: seen.update(yes=assume_yes) or 0)
    _main(monkeypatch, "push all --yes")
    assert seen["yes"] is True


@pytest.mark.parametrize(
    ("argv", "verb", "scope"),
    [
        (("pull", "all"), "pull", None),
        (("push", "ai"), "push", "ai"),
        (("cleanup", "dev_prd"), "cleanup", "dev_prd"),
    ],
)
def test_separate_argv_entries_route_to_family(monkeypatch, argv, verb, scope):
    """`route pull all` (unquoted) must fan out the same as `route "pull all"` — regression: the
    scope token was silently dropped and only the current repo was pulled."""
    seen = {}
    monkeypatch.setattr(
        route.family,
        "run_family",
        lambda v, *, assume_yes, scope: seen.update(verb=v, yes=assume_yes, scope=scope) or 0,
    )
    assert _main_argv(monkeypatch, *argv) == 0
    assert seen == {"verb": verb, "yes": False, "scope": scope}


def test_separate_argv_plain_verb_still_dispatches_to_module(monkeypatch):
    seen = {}
    monkeypatch.setattr(route, "_run", lambda module, args: seen.update(module=module, args=args) or 0)
    assert _main_argv(monkeypatch, "pull") == 0
    assert seen == {"module": "modules.toolkit.repo.pull", "args": []}


def test_plain_verb_dispatches_to_module(monkeypatch):
    seen = {}
    monkeypatch.setattr(route, "_run", lambda module, args: seen.update(module=module, args=args) or 0)
    assert _main(monkeypatch, "pull") == 0
    assert seen == {"module": "modules.toolkit.repo.pull", "args": []}


def test_cleanup_and_alias_map_to_cleanup_module(monkeypatch):
    seen = {}
    monkeypatch.setattr(route, "_run", lambda module, args: seen.update(module=module) or 0)
    _main(monkeypatch, "cleanup")
    assert seen["module"] == "modules.toolkit.repo.cleanup"
    _main(monkeypatch, "pr_cleanup")
    assert seen["module"] == "modules.toolkit.repo.cleanup"
