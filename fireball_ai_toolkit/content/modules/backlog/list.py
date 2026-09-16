"""`backlog.list` — list issues for one repo (default: the current repo) or the whole family.

uv run --no-sync python -m modules.toolkit.backlog.list [--repo vscode] [--type bug] [--label backlog]
uv run --no-sync python -m modules.toolkit.backlog.list --all [--scope ai|dev_prd]

The human output is Markdown: a `### <repo> · <count>` heading per repo followed by a
`# / Title / Labels` table (issue numbers linked, titles truncated), fenced in
`<!--sidecar:verbatim-->` markers so the Sidecar chat client renders it as-is (see
`common.utils.verbatim` and the `commentary: skip` note in `.ai/toolkit/commands/backlog.md`).
`--json` is unchanged — never fenced.
"""

from __future__ import annotations

import json

from ..common import cli
from ..common.utils import error, verbatim
from ..setup.properties import FAMILY_SCOPES, FamilyRepo, get_family_repos
from .common import ISSUE_TYPES, area_for_repo, gh, nwo, resolve_repo_or_current

_JSON_FIELDS = "number,title,state,labels,url,createdAt,updatedAt"
_TABLE_FIELDS = "number,title,labels,url"
_TITLE_WIDTH = 55


def _list_args(state: str, limit: int, issue_type: str, label_filter: str, mine: bool) -> list[str]:
    """The shared `gh issue list` argv for one repo (sans `--repo` / `--json`)."""
    args = ["issue", "list", "--state", state, "--limit", str(limit)]
    if issue_type:
        args += ["--search", f"type:{ISSUE_TYPES[issue_type]}"]
    if label_filter:
        args += ["--label", label_filter]
    if mine:
        args += ["--assignee", "@me"]
    return args


def _filter_note(issue_type: str, label_filter: str, mine: bool) -> str:
    """`"type:bug, label:backlog, assigned to you"` — `""` when nothing is filtered."""
    parts: list[str] = []
    if issue_type:
        parts.append(f"type:{issue_type}")
    if label_filter:
        parts.append(f"label:{label_filter}")
    if mine:
        parts.append("assigned to you")
    return ", ".join(parts)


def _issues(repo_nwo: str, args: list[str]) -> list[dict]:
    """The repo's matching issues as dicts (`number`, `title`, `labels`, `url`)."""
    raw = gh([*args, "--json", _TABLE_FIELDS], repo=repo_nwo).stdout.strip()
    return json.loads(raw or "[]")


def _truncate_title(title: str) -> str:
    """Collapse whitespace, clip to `_TITLE_WIDTH` with an ellipsis, and pipe-escape for a table cell."""
    flat = " ".join(title.split())
    if len(flat) > _TITLE_WIDTH:
        flat = f"{flat[: _TITLE_WIDTH - 1].rstrip()}…"
    return flat.replace("|", "\\|")


def _labels_cell(issue: dict, area: str) -> str:
    """Comma-joined label names minus the repo's own area label (redundant once grouped by repo)."""
    names = [lbl["name"] for lbl in issue.get("labels", []) if lbl.get("name") and lbl["name"] != area]
    return ", ".join(names).replace("|", "\\|") or "—"


def _table(issues: list[dict], repo: FamilyRepo) -> list[str]:
    """The Markdown table lines for one repo's issues."""
    area = area_for_repo(repo)
    lines = ["| # | Title | Labels |", "|---|---|---|"]
    for issue in issues:
        lines.append(
            f"| [#{issue['number']}]({issue['url']}) | {_truncate_title(issue['title'])} | {_labels_cell(issue, area)} |"
        )
    return lines


def _repo_section(repo: FamilyRepo, issues: list[dict]) -> list[str]:
    """`### <repo> · <count>` heading + a blank line + the table."""
    return [f"### {repo.name} · {len(issues)}", "", *_table(issues, repo)]


def _family_repos(scope: str) -> list[FamilyRepo]:
    """Every active family repo (self included, missing clones included), root-to-leaf."""
    repos = get_family_repos(include_self=True, include_missing=True, scope=scope or None)
    if not repos:
        error("no repos: map in properties.yml — --all needs a family")
    return repos


def _list_one_repo(repo: FamilyRepo, args: list[str], state: str, note: str) -> None:
    """Print one repo's issues: a `### <repo> · <n>` heading + table, or an italic empty-state line."""
    issues = _issues(nwo(repo), args)
    if not issues:
        cli.echo(verbatim(f"*No {state} issues in {repo.name}{f' ({note})' if note else ''}.*"))
        return
    lines = [f"### {repo.name} · {len(issues)}"]
    if note:
        lines += ["", f"*filtered: {note}*"]
    lines += ["", *_table(issues, repo)]
    cli.echo(verbatim("\n".join(lines)))


def _list_family(args: list[str], state: str, note: str, scope: str) -> None:
    """Print every family repo's issues as grouped Markdown tables — empty repos collapse to a
    single trailing `*N other repos: none*` line."""
    repos = _family_repos(scope)
    per_repo = [(repo, _issues(nwo(repo), args)) for repo in repos]
    total = sum(len(issues) for _, issues in per_repo)

    subtitle = f"**{total} {state} across {len(repos)} repos**"
    if scope:
        subtitle += f" · scope:{scope}"
    if note:
        subtitle += f" · {note}"
    lines = [f"## {state.capitalize()} issues — family", "", subtitle]

    empty = 0
    for repo, issues in per_repo:
        if issues:
            lines += ["", "", *_repo_section(repo, issues)]
        else:
            empty += 1

    if total == 0:
        lines += ["", f"*No {state} issues in any family repo.*"]
    elif empty:
        lines += ["", "", f"*{empty} other repo{'' if empty == 1 else 's'}: none*"]
    cli.echo(verbatim("\n".join(lines)))


def _list_family_json(args: list[str], scope: str) -> None:
    """Emit one JSON array for the whole family, each row tagged with its `repo` (`org/name`)."""
    merged: list[dict] = []
    for repo in _family_repos(scope):
        repo_nwo = nwo(repo)
        raw = gh([*args, "--json", _JSON_FIELDS], repo=repo_nwo).stdout.strip()
        merged += [{"repo": repo_nwo, **row} for row in json.loads(raw or "[]")]
    cli.echo(json.dumps(merged, indent=2))


@cli.command()
@cli.option("--repo", default="", help="Family repo (fuzzy name; default: this repo)")
@cli.option("--all", "all_repos", is_flag=True, help="Every active family repo, grouped by repo")
@cli.option("--scope", default="", help=f"With --all: limit to a family scope ({' | '.join(FAMILY_SCOPES)})")
@cli.option("--type", "issue_type", default="", help="Filter by native issue Type: bug | feature | task")
@cli.option("--label", "label_filter", default="", help="Filter by label (area or nature)")
@cli.option("--state", default="open", type=cli.Choice(["open", "closed", "all"]), help="Issue state")
@cli.option("--limit", default=30, type=int, help="Max issues to show (per repo)")
@cli.option("--mine", is_flag=True, help="Only issues assigned to you")
@cli.option("--json", "as_json", is_flag=True, help="Emit the raw gh JSON array (for scripting)")
def main(
    repo: str = "",
    all_repos: bool = False,
    scope: str = "",
    issue_type: str = "",
    label_filter: str = "",
    state: str = "open",
    limit: int = 30,
    mine: bool = False,
    as_json: bool = False,
) -> None:
    """Print the issue list as grouped Markdown tables, or the raw JSON with --json."""
    if issue_type and issue_type not in ISSUE_TYPES:
        error(f"--type must be one of {', '.join(ISSUE_TYPES)} (got {issue_type!r})")
    if all_repos and repo:
        error("--all lists the whole family — drop --repo (or drop --all to scope to one repo)")
    if scope and not all_repos:
        error("--scope only applies with --all")
    if scope and scope not in FAMILY_SCOPES:
        error(f"--scope must be one of {', '.join(FAMILY_SCOPES)} (got {scope!r})")

    args = _list_args(state, limit, issue_type, label_filter, mine)
    note = _filter_note(issue_type, label_filter, mine)

    if all_repos and as_json:
        _list_family_json(args, scope)
    elif all_repos:
        _list_family(args, state, note, scope)
    elif as_json:
        cli.echo(gh([*args, "--json", _JSON_FIELDS], repo=nwo(resolve_repo_or_current(repo))).stdout.strip() or "[]")
    else:
        _list_one_repo(resolve_repo_or_current(repo), args, state, note)


if __name__ == "__main__":
    main()
