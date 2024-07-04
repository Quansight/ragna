from pathlib import Path

from setuptools import setup
from setuptools_scm import Configuration, get_version

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent


config = Configuration.from_file(PROJECT_ROOT / "pyproject.toml")
version = get_version(
    root=str(PROJECT_ROOT),
    version_scheme=config.version_scheme,
    local_scheme=config.local_scheme,
)
install_requires = [f"{config.dist_name}=={version}"]

with open(PROJECT_ROOT / "requirements-optional.txt") as file:
    install_requires.extend(file.read().splitlines())


setup(install_requires=install_requires)
