"""Dated planning-chat tasks — start/end/list/resume chats inside the active topic. Newly wired
here (2026-08-11); the modules already existed (this repo IS the ai_vault chat/topic system) but
had no `invoke` task exposing them directly — only reachable via the prompt/skill router.
`context.run("python -m ...")`, matching every other task in this repo (see tasks/ai/repo.py's
docstring for why — no `sys.path` insert in `tasks/__init__.py` here).
"""

from invoke import task


@task
def end(context):
    """Validate the active chat has real content, then clear its active-chat tracker"""
    context.run("python -m modules.toolkit.chat.end")


@task(name="list")
def list_chats(context):
    """Show every chat file in the active topic, starring the active one"""
    context.run("python -m modules.toolkit.chat.list")


@task
def resume(context, pattern=None):
    """Reopen the chat matching pattern (filename/title substring) in the active topic"""
    flag = f' --pattern="{pattern}"' if pattern else ""
    context.run(f"python -m modules.toolkit.chat.resume{flag}")


@task
def start(context, title=None):
    """Start a new dated planning chat in the active topic"""
    flag = f' --title="{title}"' if title else ""
    context.run(f"python -m modules.toolkit.chat.start{flag}")
