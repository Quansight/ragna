import toml


def modify_pyproject(package_name):
    with open("pyproject.toml", "r") as f:
        pyproject_data = toml.load(f)

    pyproject_data["project"]["name"] = package_name

    if package_name == "ragna-base":
        pyproject_data["tool"]["setuptools"]["dynamic"]["dependencies"] = {
            "file": ["requirements-base.txt"]
        }
    else:
        pyproject_data["tool"]["setuptools"]["dynamic"]["dependencies"] = {
            "file": ["requirements.txt"]
        }

    with open("pyproject.toml", "w") as f:
        toml.dump(pyproject_data, f)


if __name__ == "__main__":
    import sys

    package_name = sys.argv[1]
    if package_name not in ["ragna", "ragna-base"]:
        print("Invalid package name. Must be 'ragna' or 'ragna-base'.")
        sys.exit(1)
    modify_pyproject(package_name)
