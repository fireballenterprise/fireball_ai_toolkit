"""Topic workspace management tasks. Newly wired here (2026-08-11); the modules already existed
but had no `invoke` task exposing them directly — only reachable via the prompt/skill router.
`context.run("python -m ...")`, matching every other task in this repo (see tasks/ai/repo.py's
docstring for why — no `sys.path` insert in `tasks/__init__.py` here).
"""

from invoke import task


@task
def init(context, description=None):
    """Initialize topic structure (chats/, docs/, instruction files) in the current directory"""
    flag = f' --description="{description}"' if description else ""
    context.run(f"python -m modules.toolkit.topic.init{flag}")


@task(name="list")
def list_topics(context, show_all=False):
    """Show the active topic, or every topic when --show-all is set"""
    flag = " --all" if show_all else ""
    context.run(f"python -m modules.toolkit.topic.list{flag}")


@task
def new(context, path, description=None):
    """Create a new topic at topics/<path> and initialize its structure"""
    flags = f' --path="{path}"'
    if description:
        flags += f' --description="{description}"'
    context.run(f"python -m modules.toolkit.topic.new{flags}")


@task
def switch(context, path):
    """Switch the active topic, auto-saving any active chat first"""
    context.run(f'python -m modules.toolkit.topic.switch --path="{path}"')


@task
def update(context, dry_run=False, current_only=False, topic=None):
    """Regenerate AGENTS.md/CLAUDE.md for every topic (or just the active/named one)"""
    flags = ""
    if dry_run:
        flags += " --dry-run"
    if current_only:
        flags += " --current-only"
    if topic:
        flags += f' --topic="{topic}"'
    context.run(f"python -m modules.toolkit.topic.update{flags}")
