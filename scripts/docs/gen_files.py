import contextlib
import io
import json
import unittest.mock

import fastapi.openapi.utils
import mkdocs_gen_files
import typer.rich_utils

from ragna.deploy import Config
from ragna.deploy._api import app as api_app
from ragna.deploy._cli import app as cli_app


def main():
    cli_reference()
    api_reference()
    config_reference()


def cli_reference():
    def get_help(command):
        with unittest.mock.patch.object(typer.rich_utils, "MAX_WIDTH", 80):
            with (
                contextlib.suppress(SystemExit),
                contextlib.redirect_stdout(io.StringIO()) as stdout,
            ):
                cli_app(([command] if command else []) + ["--help"], prog_name="ragna")

            return "\n".join(
                line.strip() for line in stdout.getvalue().strip().splitlines()
            )

    def get_doc(command):
        return (
            f"## `ragna{f' {command}' if command else ''}`\n\n"
            f"```\n{get_help(command)}\n```\n\n"
        )

    with mkdocs_gen_files.open("references/cli.md", "w") as file:
        file.write(f"# CLI reference\n\n{get_doc(None)}")
        for command in cli_app.registered_commands:
            file.write(get_doc(command.name or command.callback.__name__))


def api_reference():
    app = api_app(config=Config(), ignore_unavailable_components=False)
    openapi_json = fastapi.openapi.utils.get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    with mkdocs_gen_files.open("references/openapi.json", "w") as file:
        json.dump(openapi_json, file)


def config_reference():
    with mkdocs_gen_files.open("references/config.md", "r+") as file:
        content = file.read().replace("{{ config }}", str(Config()))
        file.seek(0)
        file.write(content)
        file.truncate()


main()
