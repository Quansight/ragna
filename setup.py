import os

from setuptools import setup

with open("requirements.txt") as f:
    ragna_dependencies = f.read().splitlines()

with open("requirements-base.txt") as f:
    base_dependencies = f.read().splitlines()

name = "ragna-base" if os.environ.get("BUILD_RAGNA_BASE") else "ragna"
dependencies = (
    base_dependencies if os.environ.get("BUILD_RAGNA_BASE") else ragna_dependencies
)

setup(
    name=name,
    install_requires=dependencies,
)
