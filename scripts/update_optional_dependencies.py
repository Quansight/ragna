import itertools
from collections import defaultdict
from functools import reduce
from pathlib import Path

import ragna
import tomlkit

from packaging.requirements import Requirement

HERE = Path(__file__).parent
PYPROJECT_TOML = HERE / ".." / "pyproject.toml"


def main():
    manual_optional_dependencies = extract_manual_optional_dependencies()
    builtin_optional_dependencies = extract_optional_dependencies()
    update_pyproject_toml(manual_optional_dependencies, builtin_optional_dependencies)


def extract_manual_optional_dependencies():
    with open(PYPROJECT_TOML) as file:
        document = tomlkit.load(file)

    optional_dependencies = defaultdict(list)
    for section in ["console", "api", "ui"]:
        for requirement_string in document["project"]["optional-dependencies"][section]:
            requirement = Requirement(requirement_string)
            optional_dependencies[requirement.name].append(requirement.specifier)

    return dict(optional_dependencies)


def extract_optional_dependencies():
    optional_dependencies = defaultdict(list)
    for cls in itertools.chain(
        ragna.builtin_config.registered_source_storage_classes.values(),
        ragna.builtin_config.registered_llm_classes.values(),
    ):
        for requirement in cls.requirements():
            if not isinstance(requirement, ragna.core.PackageRequirement):
                continue

            requirement = requirement._requirement
            optional_dependencies[requirement.name].append(requirement.specifier)
    return dict(optional_dependencies)


def update_pyproject_toml(manual_optional_dependencies, builtin_optional_dependencies):
    with open(PYPROJECT_TOML) as file:
        document = tomlkit.load(file)

    document["project"]["optional-dependencies"]["builtin-components"] = tomlkit.array(
        format_optional_dependencies(builtin_optional_dependencies)
    ).multiline(True)

    complete_optional_dependencies = defaultdict(list)
    for key in itertools.chain(
        manual_optional_dependencies.keys(), builtin_optional_dependencies.keys()
    ):
        complete_optional_dependencies[key].extend(
            manual_optional_dependencies.get(key, [])
        )
        complete_optional_dependencies[key].extend(
            builtin_optional_dependencies.get(key, [])
        )

    document["project"]["optional-dependencies"]["complete"] = tomlkit.array(
        format_optional_dependencies(complete_optional_dependencies)
    ).multiline(True)

    with open(PYPROJECT_TOML, "w") as file:
        tomlkit.dump(document, file)


def format_optional_dependencies(optional_dependencies):
    return str(
        sorted(
            (
                str(Requirement(f"{name} {reduce(lambda a, b: a & b, specifiers)}"))
                for name, specifiers in optional_dependencies.items()
            )
        )
    )


if __name__ == "__main__":
    main()
