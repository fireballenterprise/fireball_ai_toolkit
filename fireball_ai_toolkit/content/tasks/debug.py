"""Debug tasks for inspecting the local environment."""

from invoke import task


@task
def env(context):
    """Debug Commands for Environment"""
    print("\n------------")
    print("Debugging Environment")
    print("------------\n")
    context.run(
        """
        pwd &&
        env | sort
        """
    )
