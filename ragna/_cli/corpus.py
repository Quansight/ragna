import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import rich
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

from ragna._utils import default_user
from ragna.deploy._database import Database
from ragna.deploy._engine import CoreToSchemaConverter

from .config import ConfigOption

app = typer.Typer(
    name="corpus",
    help="(Experimental) Interact with a corpus of documents.",
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.callback()
def experimental_warning() -> None:
    lines = [
        (
            "[bold]ragna corpus[/bold] and all subcommands are in an experimental "
            "state and subject to change in the future."
        ),
        (
            "If you have feedback or want to suggest a feature, "
            "please open an issue at "
            "https://github.com/Quansight/ragna/issues/new/choose."
        ),
    ]
    rich.print(
        Panel("\n".join(lines), title=":rotating_light: Warning :rotating_light:")
    )


@app.command(help="Ingest documents into a given corpus.")
def ingest(
    documents: list[Path],
    metadata_fields: Annotated[
        Optional[Path],
        typer.Option(
            help="JSON file that contains mappings from document name "
            "to metadata fields associated with a document.",
        ),
    ] = None,
    corpus_name: Annotated[
        str,
        typer.Option(help="Name of the corpus to ingest the documents into."),
    ] = "default",
    config: ConfigOption = "./ragna.toml",  # type: ignore[assignment]
    user: Annotated[
        Optional[str],
        typer.Option(help="User to link the documents to in the ragna database."),
    ] = None,
    report_failures: Annotated[
        bool,
        typer.Option(help="Output to STDERR the documents that failed to be ingested."),
    ] = False,
    ignore_log: Annotated[
        bool, typer.Option(help="Ignore the log file and re-ingest all documents.")
    ] = False,
) -> None:
    try:
        document_factory = getattr(config.document, "from_path")
    except AttributeError:
        raise typer.BadParameter(
            f"{config.document.__name__} does not support creating documents from a"
            f"path. Please implement a `from_path` method."
        )

    database = Database(config.database_url)
    core_to_schema_document = CoreToSchemaConverter().document

    if metadata_fields:
        try:
            with open(metadata_fields) as file:
                metadata = json.load(file)
        except Exception:
            raise typer.BadParameter(
                f"Could not read the metadata fields file: {metadata_fields}"
            )
    else:
        metadata = {}

    if user is None:
        user = default_user()

    # Log (JSONL) for recording which files previously added to vector database.
    # Each entry has keys for 'user', 'corpus_name', 'source_storage' and 'document'.
    ingestion_log: dict[str, set[str]] = {}
    if not ignore_log:
        ingestion_log_file = Path.cwd() / ".ragna_ingestion_log.jsonl"
        if ingestion_log_file.exists():
            with open(ingestion_log_file) as stream:
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

        for source_storage in [cls() for cls in config.source_storages]:
            BATCH_SIZE = 10
            number_of_batches = len(documents) // BATCH_SIZE
            source_storage_task = progress.add_task(
                f"[green]Adding document embeddings to {source_storage.display_name()}...",
                total=number_of_batches,
            )

            for batch_number in range(0, len(documents), BATCH_SIZE):
                print(batch_number)
                documents_not_ingested = []
                document_instances = []

                if source_storage.display_name() in ingestion_log:
                    batch_doc_set = set(
                        [
                            str(doc)
                            for doc in documents[
                                batch_number : batch_number + BATCH_SIZE
                            ]
                        ]
                    )
                    if batch_doc_set.issubset(
                        ingestion_log[source_storage.display_name()]
                    ):
                        progress.advance(source_storage_task)
                        continue

                for document in documents[batch_number : batch_number + BATCH_SIZE]:
                    try:
                        document_instances.append(
                            document_factory(
                                document,
                                metadata=(
                                    metadata[str(document)]
                                    if str(document) in metadata
                                    else None
                                ),
                            )
                        )
                    except Exception:
                        documents_not_ingested.append(document)

                if not document_instances:
                    continue

                with database.get_session() as session:
                    try:
                        database.add_documents(
                            session,
                            user=user,
                            documents=[
                                core_to_schema_document(d) for d in document_instances
                            ],
                        )
                        source_storage.store(corpus_name, document_instances)
                    except Exception as exc:
                        print(exc)
                        session.rollback()
                        documents_not_ingested.extend(
                            documents[batch_number : batch_number + BATCH_SIZE]
                        )

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
                                        "source_storage": source_storage.display_name(),
                                        "document": str(document),
                                    }
                                )
                                + "\n"
                            )

                if report_failures:
                    Console(file=sys.stderr).print(
                        f"{source_storage.display_name()} failed to embed:\n{documents_not_ingested}",
                    )

                progress.advance(source_storage_task)

            progress.update(source_storage_task, completed=number_of_batches)
            progress.advance(overall_task)

        progress.update(overall_task, completed=len(config.source_storages))
