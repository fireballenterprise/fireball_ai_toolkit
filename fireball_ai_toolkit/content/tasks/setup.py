"""Repo bootstrap tasks — called by setup.sh, safe to re-run any time."""

from invoke import task

from ._targets import with_target


@task
def properties(context, repo=None):
    """Create/stamp properties.yml with this machine's repo path and git remote"""
    if with_target(repo, "setup.properties", []):
        return
    context.run("python -m modules.toolkit.setup.properties")
