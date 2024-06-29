import sys
from pathlib import Path

import toml

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"


def modify_pyproject(package_name):
    with open(PYPROJECT_TOML, "r") as f:
        pyproject_data = toml.load(f)

    pyproject_data["project"]["name"] = package_name

    pyproject_data["tool"]["setuptools"]["dynamic"]["dependencies"] = {
        "file": [
            "requirements-base.txt"
            if package_name == "ragna-base"
            else "requirements.txt"
        ]
    }

    with open(PYPROJECT_TOML, "w") as f:
        toml.dump(pyproject_data, f)


if __name__ == "__main__":
    package_name = sys.argv[1]
    if package_name not in ["ragna", "ragna-base"]:
        print("Invalid package name. Must be 'ragna' or 'ragna-base'.")
        sys.exit(1)
    modify_pyproject(package_name)
