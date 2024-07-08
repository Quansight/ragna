from collections import defaultdict
from functools import reduce
from pathlib import Path

from packaging.requirements import Requirement

import ragna
from ragna.core import Assistant, SourceStorage

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent


def main():
    optional_dependencies = make_optional_dependencies(
        extract_builtin_document_handler_requirements(),
        extract_builtin_component_requirements(),
    )

    with open(PROJECT_ROOT / "requirements-optional.txt", "w") as file:
        for dependency in optional_dependencies:
            file.write(f"{dependency}\n")


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


def append_version_specifiers(version_specifiers, obj):
    for requirement in obj.requirements():
        if not isinstance(requirement, ragna.core.PackageRequirement):
            continue

        requirement = requirement._requirement
        version_specifiers[requirement.name].append(requirement.specifier)


if __name__ == "__main__":
    main()
