import os

from setuptools import setup

print("BUILD_RAGNA_BASE=", os.environ["BUILD_RAGNA_BASE"])

with open("requirements.txt") as f:
    ragna_dependencies = f.read().splitlines()

with open("requirements-base.txt") as f:
    base_dependencies = f.read().splitlines()

is_base_build = os.environ.get("BUILD_RAGNA_BASE")

name = "ragna-base" if os.environ.get("BUILD_RAGNA_BASE") else "ragna"
dependencies = (
    base_dependencies if os.environ.get("BUILD_RAGNA_BASE") else ragna_dependencies
)

print(f"Building package: {name}")
print(
    f"Using dependencies from {'requirements-base.txt' if is_base_build else 'requirements.txt'}"
)

setup(
    name=name,
    install_requires=dependencies,
)
