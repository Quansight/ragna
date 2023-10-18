import contextlib
import io
import unittest.mock
from pathlib import Path

import typer.rich_utils

from mkdocs.config.defaults import MkDocsConfig

from ragna._cli import app

HERE = Path(__file__).parent
DOCS_ROOT = HERE.parent


def on_pre_build(config: MkDocsConfig) -> None:
    with open(DOCS_ROOT / "references" / "cli.md", "w") as file:
        file.write(f"# CLI reference\n\n{get_doc(None)}")
        for command in app.registered_commands:
            file.write(get_doc(command.name or command.callback.__name__))


def get_doc(command):
    return (
        f"## `ragna{f' {command}' if command else ''}`\n\n"
        f"```\n{get_help(command)}\n```\n\n"
    )


def get_help(command):
    with unittest.mock.patch.object(typer.rich_utils, "MAX_WIDTH", 80):
        with contextlib.suppress(SystemExit), contextlib.redirect_stdout(
            io.StringIO()
        ) as stdout:
            app(([command] if command else []) + ["--help"], prog_name="ragna")

        return "\n".join(
            line.strip() for line in stdout.getvalue().strip().splitlines()
        )
