import os

import nox


@nox.session(name="build")
def build(session):
    setup_script = "scripts/pyproject.toml"
    symlink_pyproject(setup_script)
    session.install("build")
    session.run("python", "-m", "build")


@nox.session(name="build-base")
def build_bar(session):
    setup_script = "scripts/pyproject-base.toml"
    symlink_pyproject(setup_script)
    session.install("build")
    session.run("python", "-m", "build")


def symlink_pyproject(script):
    if os.path.exists(script):
        # Remove existing pyproject.toml if it exists
        if os.path.exists("pyproject.toml"):
            os.remove("pyproject.toml")
        os.symlink(script, "pyproject.toml")
