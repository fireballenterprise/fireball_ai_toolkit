"""Screenshot workflow tasks — wraps `modules/screenshots/*.py`. `context.run("python -m ...")`,
not a direct import, matching every other task in this repo (see tasks/ai/repo.py's docstring).
"""

from invoke import task


@task
def clean(context, confirm=True):
    """Delete screenshot images from the screenshots/ folder (--confirm/--no-confirm, default: confirm)"""
    flag = "--confirm" if confirm else "--no-confirm"
    context.run(f"python -m modules.toolkit.screenshots.clean {flag}")


@task
def configure(context):
    """Configure macOS to save screenshots into the repo's screenshots/ folder"""
    context.run("python -m modules.toolkit.screenshots.configure")


@task
def view(context):
    """Copy the latest screenshot to screenshots/latest.png for AI viewing"""
    context.run("python -m modules.toolkit.screenshots.view")
