from typing import Any


def fix_module(globals: dict[str, Any]) -> None:
    """Fix the __module__ attribute on public objects to hide internal structure.

    Put the following snippet at the end of public `__init__.py` files of ragna
    subpackages. This will hide any internally private structure.

    ```python
    from ragna._utils import fix_module  # usort: skip

    fix_module(globals())
    del fix_module
    ```
    """
    for name, obj in globals.items():
        if name.startswith("_"):
            continue

        obj.__module__ = globals["__package__"]
