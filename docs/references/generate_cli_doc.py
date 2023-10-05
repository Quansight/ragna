import contextlib
import io
from pathlib import Path

from ragna._cli import app


def get_help(*args):
    with contextlib.suppress(SystemExit), contextlib.redirect_stdout(
        io.StringIO()
    ) as stdout:
        app(list(args) + ["--help"])

    return stdout.getvalue().strip().replace(Path(__file__).name, "ragna")


with open(Path(__file__).parent / "cli.md", "w") as file:
    file.write("# CLI reference\n\n")

    file.write(f"## `ragna`\n\n```\n{get_help()}\n```\n\n")

    for command in app.registered_commands:
        name = command.name or command.callback.__name__

        file.write(f"## `ragna {name}`\n\n```\n{get_help(name)}\n```\n\n")
