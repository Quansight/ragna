import importlib
from pathlib import Path

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent
PACKAGE_ROOT = PROJECT_ROOT / "ragna"


def main():
    for path in PACKAGE_ROOT.rglob("*.py"):
        if path.name == "__init__.py":
            path = path.parent
        else:
            path = path.with_suffix("")

        if path.name.startswith("_"):
            continue

        name = path.relative_to(PROJECT_ROOT).as_posix().replace("/", ".")

        try:
            importlib.import_module(name)
        except Exception as exc:
            raise ImportError(
                f"Trying to import '{name}' raise the error above"
            ) from exc
        else:
            print(name)


if __name__ == "__main__":
    main()
