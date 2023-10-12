import itertools
from collections import defaultdict
from functools import reduce
from pathlib import Path

import ragna
import tomlkit
import tomlkit.items

from packaging.requirements import Requirement
from ragna.core import Assistant, DocumentHandler, SourceStorage

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
    for module, cls in [
        (ragna.document_handlers, DocumentHandler),
        (ragna.source_storages, SourceStorage),
        (ragna.assistants, Assistant),
    ]:
        for obj in module.__dict__.values():
            if not (isinstance(obj, type) and issubclass(obj, cls)):
                continue

            for requirement in obj.requirements():
                if not isinstance(requirement, ragna.core.PackageRequirement):
                    continue

                requirement = requirement._requirement
                optional_dependencies[requirement.name].append(requirement.specifier)

    return dict(optional_dependencies)


def update_pyproject_toml(manual_optional_dependencies, builtin_optional_dependencies):
    with open(PYPROJECT_TOML) as file:
        document = tomlkit.load(file)

    document["project"]["optional-dependencies"]["builtin-components"] = to_array(
        builtin_optional_dependencies
    )

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

    document["project"]["optional-dependencies"]["complete"] = to_array(
        complete_optional_dependencies
    )

    with open(PYPROJECT_TOML, "w") as file:
        tomlkit.dump(document, file)


def to_array(optional_dependencies):
    value = sorted(
        (
            str(Requirement(f"{name} {reduce(lambda a, b: a & b, specifiers)}"))
            for name, specifiers in optional_dependencies.items()
        )
    )
    return tomlkit.items.Array(
        list(map(tomlkit.items.String.from_raw, value)),
        trivia=tomlkit.items.Trivia(),
        multiline=True,
    )


if __name__ == "__main__":
    main()
