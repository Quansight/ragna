from collections import defaultdict
from functools import reduce
from pathlib import Path

from packaging.requirements import Requirement

import ragna
from ragna.core import Assistant, SourceStorage

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent
REQUIREMENTS_TXT = PROJECT_ROOT / "requirements.txt"
REQUIREMENTS_BASE_TXT = PROJECT_ROOT / "requirements-base.txt"


def main():
    optional_dependencies = make_optional_dependencies(
        extract_builtin_document_handler_requirements(),
        extract_builtin_component_requirements(),
    )
    create_requirements_txt(optional_dependencies)


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


def create_requirements_txt(optional_dependencies):
    # Read existing dependencies from requirements-base.txt
    existing_dependencies = set()
    if REQUIREMENTS_BASE_TXT.exists():
        with open(REQUIREMENTS_BASE_TXT, "r") as file:
            existing_dependencies = set(line.strip() for line in file)

    # Add optional dependencies
    all_dependencies = existing_dependencies.union(optional_dependencies)

    # Sort the dependencies to maintain a consistent order
    sorted_dependencies = sorted(all_dependencies)

    # Overwrite the requirements.txt file with the sorted dependencies
    with open(REQUIREMENTS_TXT, "w") as file:
        file.write("\n".join(sorted_dependencies))
        file.write("\n")


def append_version_specifiers(version_specifiers, obj):
    for requirement in obj.requirements():
        if not isinstance(requirement, ragna.core.PackageRequirement):
            continue

        requirement = requirement._requirement
        version_specifiers[requirement.name].append(requirement.specifier)


if __name__ == "__main__":
    main()
