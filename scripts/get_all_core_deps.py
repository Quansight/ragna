from collections import defaultdict
from functools import reduce

import tomlkit
from packaging.requirements import Requirement


def main(files):
    deps = defaultdict(list)
    for file in files:
        with open(file) as fh:
            document = tomlkit.load(fh)

        # This assumes setuptools as backend. You can probably switch based on the build backend
        for dep in document["project"]["dependencies"]:
            req = Requirement(dep)
            deps[req.name].append(req.specifier)

    joint_deps = sorted(
        (
            str(Requirement(f"{name} {reduce(lambda a, b: a & b, specifiers)}"))
            for name, specifiers in deps.items()
        )
    )
    print("\n".join(joint_deps))


if __name__ == "__main__":
    main(["../pyproject.toml", "../another_pyproject.toml"])
