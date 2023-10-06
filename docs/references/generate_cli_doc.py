import contextlib
import io
from pathlib import Path

from ragna._cli import app


def main():
    with open(Path(__file__).parent / "cli.md", "w") as file:
        file.write(f"# CLI reference\n\n{get_doc(None)}")
        for command in app.registered_commands:
            file.write(get_doc(command.name or command.callback.__name__))


def get_doc(command):
    return f"## `ragna{f' {command}' if command else ''}`\n\n```\n{get_help(command)}\n```\n\n"


def get_help(command):
    with contextlib.suppress(SystemExit), contextlib.redirect_stdout(
        io.StringIO()
    ) as stdout:
        app(([command] if command else []) + ["--help"])

    lines = stdout.getvalue().strip().splitlines()
    lines[0] = lines[0].replace(Path(__file__).name, "ragna")
    return "\n".join(line.strip() for line in lines)


if __name__ == "__main__":
    main()
