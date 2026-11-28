"""Git/PR workflow tasks — wraps `modules/repo/*.py`. `context.run("python -m ...")`, not a
direct import, matching every other task in this repo — this repo's own `tasks/__init__.py`
never adds the repo root to `sys.path`, so a direct `from modules.repo import ...` import would
fail; subprocess-invoking the module lets Python's own `-m` resolve it against the CWD instead.

`--scope` picks the repos from `properties.yml` `repos:` (org > repo; `status: retired` skipped, `ai`, `default_branch` and
`parent` drive the scopes and the root-to-leaf order): `all` | `ai` | `dev_prd` | one or more repo names (`name` or `org/name`,
comma-separated). `pull` and `cleanup` default to `all` (the whole family); `push` and `sync` default to this repo (they commit,
so fanning out stays explicit). `--repo <name|path>` runs a verb against one other managed checkout.
"""

from invoke import task

from ._targets import with_target


def _repo_flag(repo):
    return f" --repo {repo}" if repo else ""


SCOPE_HELP = "all (default for pull/cleanup) | ai | dev_prd | repo names (name or org/name, comma-separated)"


def _family(context, verb, scope):
    context.run(f'python -m modules.fireball_ai_toolkit.repo.route "{verb} --scope={scope}"')


@task(help={"scope": SCOPE_HELP, "repo": "One other managed checkout instead (name or path)"})
def pull(context, scope="all", repo=None):
    """Pull the family (default) or --scope's repos: each on its verified default branch, stash, pull --ff-only, restore"""
    if repo:
        context.run(f'python -m modules.fireball_ai_toolkit.repo.route "pull{_repo_flag(repo)}"')
        return
    _family(context, "pull", scope)


@task(
    help={
        "scope": SCOPE_HELP.replace("default for pull/cleanup", "default: this repo"),
        "repo": "One other managed checkout",
    }
)
def push(context, no_confirm=False, scope=None, repo=None):
    """Push this repo (fix → test → commit → push); --scope for the family or named repos, --repo for one other checkout"""
    if scope:
        _family(context, "push", scope)
        return
    if repo:
        context.run(f'python -m modules.fireball_ai_toolkit.repo.route "push{_repo_flag(repo)}"')
        return
    flag = " --no-confirm" if no_confirm else ""
    context.run(f"python -m modules.fireball_ai_toolkit.repo.push{flag}")


@task(help={"scope": SCOPE_HELP.replace("default for pull/cleanup", "default: this repo")})
def sync(context, scope=None, no_confirm=False, no_tests=False):
    """Pull (auto-resolving lock/binary conflicts), then fix → test → commit → push; --scope for the family or named repos"""
    if scope:
        _family(context, "sync", scope)
        return
    flags = (" --no-confirm" if no_confirm else "") + (" --no-tests" if no_tests else "")
    context.run(f"python -m modules.fireball_ai_toolkit.repo.sync{flags}")


@task(help={"scope": SCOPE_HELP, "repo": "One other managed checkout instead (name or path)"})
def cleanup(context, scope="all", repo=None):
    """Clean up merged feature branches and sweep local build/cache trash across the family (default) or --scope's repos"""
    if repo:
        context.run(f'python -m modules.fireball_ai_toolkit.repo.route "cleanup{_repo_flag(repo)}"')
        return
    _family(context, "cleanup", scope)


@task()
def pr_cleanup(context):
    """Deprecated alias for `cleanup`"""
    cleanup(context)


@task()
def list_family(context):
    """Show the repos:/lineage: family map from properties.yml"""
    context.run('python -m modules.fireball_ai_toolkit.repo.route "list"')


@task()
def pr_push(context, confirm=True):
    """Push the current feature branch (--confirm/--no-confirm, default: confirm)"""
    flag = "--confirm" if confirm else "--no-confirm"
    context.run(f"python -m modules.fireball_ai_toolkit.repo.pr_push {flag}")


@task()
def rebase(context, repo=None):
    """Rebase onto remote default branch (optionally squash first)"""
    if with_target(repo, "repo.rebase", []):
        return
    context.run("python -m modules.fireball_ai_toolkit.repo.rebase")


@task()
def squash(context, repo=None):
    """Anchored squash of all commits to root with optional force push"""
    if with_target(repo, "repo.squash", []):
        return
    context.run("python -m modules.fireball_ai_toolkit.repo.squash")


@task()
def pr_diff(context):
    """Show current branch's commit log/diff vs. its detected base branch"""
    context.run("python -m modules.fireball_ai_toolkit.repo.pr_diff")


@task()
def pr_notes_save(context, content=None):
    """Save PR notes to tmp/pull_requests/ (--content=...)"""
    flag = f' --content="{content}"' if content else ""
    context.run(f"python -m modules.fireball_ai_toolkit.repo.pr_notes{flag}")


@task()
def pr_create(context, title=None, content=None):
    """Open a GitHub PR for the current branch (gh pr create)"""
    flags = ""
    if title:
        flags += f' --title="{title}"'
    if content:
        flags += f' --content="{content}"'
    context.run(f"python -m modules.fireball_ai_toolkit.repo.pr_create{flags}")
