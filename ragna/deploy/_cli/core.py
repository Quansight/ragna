import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated, Optional

import httpx
import rich
import typer
import uvicorn
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

import ragna
from ragna._utils import timeout_after
from ragna.core._utils import default_user
from ragna.deploy._api import app as api_app
from ragna.deploy._api import database, orm
from ragna.deploy._ui import app as ui_app

from .config import ConfigOption, check_config, init_config

app = typer.Typer(
    name="ragna",
    invoke_without_command=True,
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)
corpus_app = typer.Typer()
app.add_typer(corpus_app, name="corpus")


def version_callback(value: bool) -> None:
    if value:
        rich.print(f"ragna {ragna.__version__} from {ragna.__path__[0]}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", callback=version_callback, help="Show version and exit."
        ),
    ] = None,
) -> None:
    pass


@app.command(help="Start a wizard to build a Ragna configuration interactively.")
def init(
    *,
    output_path: Annotated[
        Path,
        typer.Option(
            "-o",
            "--output-file",
            metavar="OUTPUT_PATH",
            default_factory=lambda: Path.cwd() / "ragna.toml",
            show_default="./ragna.toml",
            help="Write configuration to <OUTPUT_PATH>.",
        ),
    ],
    force: Annotated[
        bool,
        typer.Option(
            "-f", "--force", help="Overwrite an existing file at <OUTPUT_PATH>."
        ),
    ] = False,
) -> None:
    config, output_path, force = init_config(output_path=output_path, force=force)
    config.to_file(output_path, force=force)


@app.command(help="Check the availability of components.")
def check(config: ConfigOption = "./ragna.toml") -> None:  # type: ignore[assignment]
    is_available = check_config(config)
    raise typer.Exit(int(not is_available))


@app.command(help="Start the REST API.")
def api(
    *,
    config: ConfigOption = "./ragna.toml",  # type: ignore[assignment]
    ignore_unavailable_components: Annotated[
        bool,
        typer.Option(
            help=(
                "Ignore components that are not available, "
                "i.e. their requirements are not met. "
            )
        ),
    ] = False,
) -> None:
    uvicorn.run(
        api_app(
            config=config, ignore_unavailable_components=ignore_unavailable_components
        ),
        host=config.api.hostname,
        port=config.api.port,
    )


@app.command(help="Start the web UI.")
def ui(
    *,
    config: ConfigOption = "./ragna.toml",  # type: ignore[assignment]
    start_api: Annotated[
        Optional[bool],
        typer.Option(
            help="Start the ragna REST API alongside the web UI in a subprocess.",
            show_default="Start if the API is not served at the configured URL.",
        ),
    ] = None,
    ignore_unavailable_components: Annotated[
        bool,
        typer.Option(
            help=(
                "Ignore components that are not available, "
                "i.e. their requirements are not met. "
                "This option as no effect if --no-start-api is used."
            )
        ),
    ] = False,
    open_browser: Annotated[
        bool,
        typer.Option(help="Open the web UI in the browser when it is started."),
    ] = True,
) -> None:
    def check_api_available() -> bool:
        try:
            return httpx.get(config.api.url).is_success
        except httpx.ConnectError:
            return False

    if start_api is None:
        start_api = not check_api_available()

    if start_api:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "ragna",
                "api",
                "--config",
                config.__ragna_cli_config_path__,  # type: ignore[attr-defined]
                f"--{'' if ignore_unavailable_components else 'no-'}ignore-unavailable-components",
            ],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    else:
        process = None

    try:
        if process is not None:

            @timeout_after(60)
            def wait_for_api() -> None:
                while not check_api_available():
                    time.sleep(0.5)

            try:
                wait_for_api()
            except TimeoutError:
                rich.print(
                    "Failed to start the API in 60 seconds. "
                    "Please start it manually with [bold]ragna api[/bold]."
                )
                raise typer.Exit(1)

        ui_app(config=config, open_browser=open_browser).serve()  # type: ignore[no-untyped-call]
    finally:
        if process is not None:
            process.kill()
            process.communicate()


@corpus_app.command(help="Ingest some documents into a given corpus.")
def ingest(
    documents: list[Path],
    corpus_name: Optional[str] = typer.Option(
        None, help="Name of the corpus to ingest the documents into."
    ),
    config: ConfigOption = "./ragna.toml",  # type: ignore[assignment]
    user: Optional[str] = typer.Option(
        None, help="User to link the documents to in the ragna database."
    ),
    report_failures: bool = typer.Option(
        False, help="Output to STDERR the documents that failed to be ingested."
    ),
    ignore_log: bool = typer.Option(
        False, help="Ignore the log file and re-ingest all documents."
    ),
) -> None:
    try:
        document_factory = getattr(config.document, "from_path")
    except AttributeError:
        raise typer.BadParameter(
            f"{config.document.__name__} does not support creating documents from a path. "
            "Please implement a `from_path` method."
        )

    try:
        make_session = database.get_sessionmaker(config.api.database_url)
    except Exception:
        raise typer.BadParameter(
            f"Could not connect to the database: {config.api.database_url}"
        )

    if user is None:
        user = default_user()
    with make_session() as session:  # type: ignore[attr-defined]
        user_id = database._get_user_id(session, user)

    # Log (JSONL) for recording which files previously added to vector database.
    # Each entry has keys for 'user', 'corpus_name', 'source_storage' and 'document'.
    ingestion_log: dict[str, set[str]] = {}
    if not ignore_log:
        ingestion_log_file = Path.cwd() / ".ragna_ingestion_log.jsonl"
        if ingestion_log_file.exists():
            with open(ingestion_log_file, "r") as stream:
                for line in stream:
                    entry = json.loads(line)
                    if entry["corpus_name"] == corpus_name and entry["user"] == user:
                        ingestion_log.setdefault(entry["source_storage"], set()).add(
                            entry["document"]
                        )

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.1f}%",
        TimeRemainingColumn(),
    ) as progress:
        overall_task = progress.add_task(
            "[cyan]Adding document embeddings to source storages...",
            total=len(config.source_storages),
        )

        for source_storage in config.source_storages:
            BATCH_SIZE = 10
            number_of_batches = len(documents) // BATCH_SIZE
            source_storage_task = progress.add_task(
                f"[green]Adding document embeddings to {source_storage.__name__}...",
                total=number_of_batches,
            )

            for batch_number in range(0, len(documents), BATCH_SIZE):
                documents_not_ingested = []
                document_instances = []
                orm_documents = []

                if source_storage.__name__ in ingestion_log:
                    batch_doc_set = set(
                        [
                            str(doc)
                            for doc in documents[
                                batch_number : batch_number + BATCH_SIZE
                            ]
                        ]
                    )
                    if batch_doc_set.issubset(ingestion_log[source_storage.__name__]):
                        progress.advance(source_storage_task)
                        continue

                for document in documents[batch_number : batch_number + BATCH_SIZE]:
                    try:
                        doc_instance = document_factory(document)
                        document_instances.append(doc_instance)
                        orm_documents.append(
                            orm.Document(
                                id=doc_instance.id,
                                user_id=user_id,
                                name=doc_instance.name,
                                metadata_=doc_instance.metadata,
                            )
                        )
                    except Exception:
                        documents_not_ingested.append(document)

                if not orm_documents:
                    continue

                try:
                    session = make_session()
                    session.add_all(orm_documents)
                    source_storage().store(corpus_name, document_instances)
                    session.commit()
                except Exception:
                    documents_not_ingested.extend(
                        documents[batch_number : batch_number + BATCH_SIZE]
                    )
                    session.rollback()
                finally:
                    session.close()

                if not ignore_log:
                    with open(ingestion_log_file, "a") as stream:
                        for document in documents[
                            batch_number : batch_number + BATCH_SIZE
                        ]:
                            stream.write(
                                json.dumps(
                                    {
                                        "user": user,
                                        "corpus_name": corpus_name,
                                        "source_storage": source_storage.__name__,
                                        "document": str(document),
                                    }
                                )
                                + "\n"
                            )

                if report_failures:
                    Console(file=sys.stderr).print(
                        f"{source_storage.__name__} failed to embed:\n{documents_not_ingested}",
                    )

                progress.advance(source_storage_task)

            progress.update(source_storage_task, completed=number_of_batches)
            progress.advance(overall_task)

        progress.update(overall_task, completed=len(config.source_storages))
