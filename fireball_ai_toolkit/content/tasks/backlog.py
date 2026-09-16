"""GitHub-Issues backlog tasks — track bugs / features / tasks per family repo (see
`modules/toolkit/backlog/`). `context.run("python -m ...")`, matching every other task here."""

import shlex

from invoke import task

_MODULE = "modules.toolkit.backlog"


def _run(context, verb, *pairs, flags=()):
    """`python -m modules.toolkit.backlog.<verb>` with `--key value` pairs (skipping empty
    values) and bare `--flag`s. Every value is `shlex.quote`d — issue titles / bodies / comments
    routinely contain quotes, parens, backticks, and `$`."""
    parts = [f"python -m {_MODULE}.{verb}"]
    for key, value in pairs:
        if value not in (None, ""):
            parts.append(f"--{key} {shlex.quote(str(value))}")
    parts.extend(f"--{flag}" for flag in flags)
    context.run(" ".join(parts))


@task(help={"repo": "target family repo (fuzzy name)", "type": "bug | feature | task", "title": "issue title"})
def add(context, repo=None, type=None, title=None, body="", images="", area="", label="", web=False):  # noqa: A002
    """Open a GitHub Issue on a family repo (native Type + area/nature labels)"""
    _run(
        context,
        "add",
        ("repo", repo),
        ("type", type),
        ("title", title),
        ("body", body),
        ("images", images),
        ("area", area),
        ("label", label),
        flags=["web"] if web else [],
    )


@task
def close(context, repo=None, number=None, pr="", sha="", reason="completed", comment=""):
    """Close an issue, optionally noting the PR / sha that fixed it"""
    _run(
        context,
        "close",
        ("repo", repo),
        ("number", number),
        ("reason", reason),
        ("pr", pr),
        ("sha", sha),
        ("comment", comment),
    )


@task
def comment(context, repo=None, number=None, body=None, images=""):
    """Add a comment to an issue"""
    _run(context, "comment", ("repo", repo), ("number", number), ("body", body), ("images", images))


@task(name="list")
def list_issues(context, repo="", type="", label="", state="open", limit=30, mine=False, json=False):  # noqa: A002
    """List a repo's issues (defaults to this repo)"""
    _run(
        context,
        "list",
        ("repo", repo),
        ("type", type),
        ("label", label),
        ("state", state),
        ("limit", limit),
        flags=[flag for flag, on in (("mine", mine), ("json", json)) if on],
    )


@task
def start(context, repo=None, number=None, comment=""):
    """Show + self-assign an issue and print the repo's ship rules"""
    _run(context, "start", ("repo", repo), ("number", number), ("comment", comment))


@task
def view(context, repo=None, number=None, json=False):  # noqa: A002
    """Show one issue"""
    _run(context, "view", ("repo", repo), ("number", number), flags=["json"] if json else [])
