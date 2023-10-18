def fix_module(globals):
    for name, obj in globals.items():
        if name.startswith("_"):
            continue

        obj.__module__ = globals["__package__"]
