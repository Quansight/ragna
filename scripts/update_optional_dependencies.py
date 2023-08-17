from collections import defaultdict
from functools import reduce
from pathlib import Path

import ragna.extensions
import tomlkit

from packaging.requirements import Requirement

from ragna._backend import Component


def main():
    optional_dependencies = extract_optional_dependencies()
    update_pyproject_toml(optional_dependencies)


def extract_optional_dependencies():
    optional_dependencies = defaultdict(list)
    for obj in ragna.extensions.__dict__.values():
        if not is_true_subclass(obj, Component):
            continue

        for requirement in obj.requirements():
            if not isinstance(requirement, ragna.extensions.PackageRequirement):
                continue

            requirement = requirement._requirement
            optional_dependencies[requirement.name].append(requirement.specifier)

    return sorted(
        (
            str(Requirement(f"{name} {reduce(lambda a, b: a & b, specifiers)}"))
            for name, specifiers in optional_dependencies.items()
        )
    )


def update_pyproject_toml(optional_dependencies):
    here = Path(__file__).parent
    path = here / ".." / "pyproject.toml"

    with open(path) as file:
        document = tomlkit.load(file)

    document["project"]["optional-dependencies"]["extensions"] = tomlkit.array(
        str(optional_dependencies)
    ).multiline(True)

    with open(path, "w") as file:
        tomlkit.dump(document, file)


def is_true_subclass(obj, cls):
    return isinstance(obj, type) and issubclass(obj, cls) and type(obj) is not cls


if __name__ == "__main__":
    main()
