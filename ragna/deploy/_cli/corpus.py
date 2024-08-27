import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

from ragna.core._utils import default_user
from ragna.deploy._api import database, orm

from .config import ConfigOption

app = typer.Typer(
    name="corpus",
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.command(help="Ingest some documents into a given corpus.")
def ingest(
    documents: list[Path],
    metadata_fields: Optional[Path] = typer.Option(
        None,
        help="JSON file that contains mappings from document name "
        "to metadata fields associated with a document.",
    ),
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

    if metadata_fields:
        try:
            with open(metadata_fields, "r") as f:
                metadata = json.load(f)
        except Exception:
            raise typer.BadParameter(
                f"Could not read the metadata fields file: {metadata_fields}"
            )
    else:
        metadata = {}

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
                        doc_instance = document_factory(
                            document,
                            metadata=(
                                metadata[str(document)]
                                if str(document) in metadata
                                else None
                            ),
                        )
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
