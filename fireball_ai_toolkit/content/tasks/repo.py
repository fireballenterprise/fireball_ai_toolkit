"""Git/PR workflow tasks — wraps `modules/repo/*.py`. `context.run("python -m ...")`, not a
direct import, matching every other task in this repo — this repo's own `tasks/__init__.py`
never adds the repo root to `sys.path`, so a direct `from modules.repo import ...` import would
fail; subprocess-invoking the module lets Python's own `-m` resolve it against the CWD instead.

`--repo <name|path>` on `pull` / `push` / `cleanup` / `rebase` / `squash` runs the verb against
another managed checkout (mutually exclusive with `--family`); everything else is current-repo only.
"""

from invoke import task

from ._targets import with_target


def _repo_flag(repo):
    return f" --repo {repo}" if repo else ""


@task
def pull(context, family=False, repo=None):
    """Pull updates from git remote; --family for the whole family, --repo for one other checkout"""
    if family:
        context.run('python -m modules.toolkit.repo.route "pull all"')
        return
    context.run(f'python -m modules.toolkit.repo.route "pull{_repo_flag(repo)}"')


@task
def push(context, no_confirm=False, family=False, repo=None):
    """Push to git remote and iCloud (fix → test → commit → push); --family / --repo"""
    if family:
        context.run('python -m modules.toolkit.repo.route "push all"')
        return
    if repo:
        context.run(f'python -m modules.toolkit.repo.route "push{_repo_flag(repo)}"')
        return
    flag = " --no-confirm" if no_confirm else ""
    context.run(f"python -m modules.toolkit.repo.push{flag}")


@task
def cleanup(context, family=False, repo=None):
    """Clean up a merged feature branch, then sweep local build/cache trash; --family / --repo"""
    if family:
        context.run('python -m modules.toolkit.repo.route "cleanup all"')
        return
    context.run(f'python -m modules.toolkit.repo.route "cleanup{_repo_flag(repo)}"')


@task
def pr_cleanup(context):
    """Deprecated alias for `cleanup`"""
    cleanup(context)


@task
def list_family(context):
    """Show the repos:/lineage: family map from properties.yml"""
    context.run('python -m modules.toolkit.repo.route "list"')


@task
def pr_push(context, confirm=True):
    """Push the current feature branch (--confirm/--no-confirm, default: confirm)"""
    flag = "--confirm" if confirm else "--no-confirm"
    context.run(f"python -m modules.toolkit.repo.pr_push {flag}")


@task
def rebase(context, repo=None):
    """Rebase onto remote default branch (optionally squash first)"""
    if with_target(repo, "repo.rebase", []):
        return
    context.run("python -m modules.toolkit.repo.rebase")


@task
def squash(context, repo=None):
    """Anchored squash of all commits to root with optional force push"""
    if with_target(repo, "repo.squash", []):
        return
    context.run("python -m modules.toolkit.repo.squash")


@task
def pr_diff(context):
    """Show current branch's commit log/diff vs. its detected base branch"""
    context.run("python -m modules.toolkit.repo.pr_diff")


@task
def pr_notes_save(context, content=None):
    """Save PR notes to tmp/pull_requests/ (--content=...)"""
    flag = f' --content="{content}"' if content else ""
    context.run(f"python -m modules.toolkit.repo.pr_notes{flag}")


@task
def pr_create(context, title=None, content=None):
    """Open a GitHub PR for the current branch (gh pr create)"""
    flags = ""
    if title:
        flags += f' --title="{title}"'
    if content:
        flags += f' --content="{content}"'
    context.run(f"python -m modules.toolkit.repo.pr_create{flags}")
