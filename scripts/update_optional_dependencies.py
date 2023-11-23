from collections import defaultdict
from functools import reduce
from pathlib import Path

import tomlkit
import tomlkit.items
from packaging.requirements import Requirement

import ragna
from ragna.core import Assistant, SourceStorage

HERE = Path(__file__).parent
PYPROJECT_TOML = HERE / ".." / "pyproject.toml"


def main():
    optional_dependencies = make_optional_dependencies(
        extract_builtin_document_handler_requirements(),
        extract_builtin_component_requirements(),
    )
    update_pyproject_toml(optional_dependencies)


def make_optional_dependencies(*optional_requirements):
    optional_dependencies = defaultdict(list)
    for requirements in optional_requirements:
        for name, specifiers in requirements.items():
            optional_dependencies[name].extend(specifiers)

    return sorted(
        str(Requirement(f"{name} {reduce(lambda a, b: a & b, specifiers)}"))
        for name, specifiers in optional_dependencies.items()
    )


def extract_builtin_document_handler_requirements():
    requirements = defaultdict(list)
    for obj in ragna.core.__dict__.values():
        if (
            isinstance(obj, type) and issubclass(obj, ragna.core.DocumentHandler)
        ) and obj is not ragna.core.DocumentHandler:
            append_version_specifiers(requirements, obj)

    return dict(requirements)


def extract_builtin_component_requirements():
    requirements = defaultdict(list)
    for module, cls in [
        (ragna.source_storages, SourceStorage),
        (ragna.assistants, Assistant),
    ]:
        for obj in module.__dict__.values():
            if isinstance(obj, type) and issubclass(obj, cls):
                append_version_specifiers(requirements, obj)

    return dict(requirements)


def update_pyproject_toml(optional_dependencies):
    with open(PYPROJECT_TOML) as file:
        document = tomlkit.load(file)

    document["project"]["optional-dependencies"]["all"] = tomlkit.items.Array(
        list(map(tomlkit.items.String.from_raw, optional_dependencies)),
        trivia=tomlkit.items.Trivia(),
        multiline=True,
    )

    with open(PYPROJECT_TOML, "w") as file:
        tomlkit.dump(document, file)


def append_version_specifiers(version_specifiers, obj):
    for requirement in obj.requirements():
        if not isinstance(requirement, ragna.core.PackageRequirement):
            continue

        requirement = requirement._requirement
        version_specifiers[requirement.name].append(requirement.specifier)


if __name__ == "__main__":
    main()
