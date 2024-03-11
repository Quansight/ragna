import uuid

from typing import cast

import ragna
from ragna.core import Document, PackageRequirement, Requirement, Source

from ._vector_database import VectorDatabaseSourceStorage

from ._embedding_model import Embedding
import pyarrow as pa

class LanceDB(VectorDatabaseSourceStorage):
    """[LanceDB vector database](https://lancedb.com/)

    !!! info "Required packages"

        - `chromadb>=0.4.13`
        - `lancedb>=0.2`
        - `pyarrow`
    """

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            *super().requirements(),
            PackageRequirement("lancedb>=0.2"),
            PackageRequirement(
                "pyarrow",
                # See https://github.com/apache/arrow/issues/38167
                exclude_modules=["__dummy__"],
            ),
        ]

    def __init__(self) -> None:
        super().__init__()

        import lancedb

        self._db = lancedb.connect(ragna.local_root() / "lancedb")

    _VECTOR_COLUMN_NAME = "embedded_text"

    def store(
        self,
        documents: list[Embedding],
        *,
        chat_id: uuid.UUID,
    ) -> None:
        _schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("document_id", pa.string()),
                pa.field("page_numbers", pa.string()),
                pa.field("text", pa.string()),
                pa.field(
                    self._VECTOR_COLUMN_NAME,
                    pa.list_(pa.float32(), len(documents[0].embedding)),
                ),
                pa.field("num_tokens", pa.int32()),
            ]
        )

        table = self._db.create_table(name=str(chat_id), schema=_schema)

        for embedding in documents:
            table.add(
                [
                    {
                        "id": str(uuid.uuid4()),
                        "document_id": str(embedding.chunk.document_id),
                        "page_numbers": self._page_numbers_to_str(
                            embedding.chunk.page_numbers
                        ),
                        "text": embedding.chunk.text,
                        self._VECTOR_COLUMN_NAME: embedding.embedding,
                        "num_tokens": embedding.chunk.num_tokens,
                    }
                ]
            )

    def retrieve(
        self,
        documents: list[Document],
        prompt: list[float],
        *,
        chat_id: uuid.UUID,
    ) -> list[Source]:
        table = self._db.open_table(str(chat_id))

        # We cannot retrieve source by a maximum number of tokens. Thus, we estimate how
        # many sources we have to query. We overestimate by a factor of two to avoid
        # retrieving to few sources and needed to query again.
        limit = int(num_tokens * 2 / chunk_size)
        results = (
            table.search(
                prompt,
                vector_column_name=self._VECTOR_COLUMN_NAME,
            )
            .limit(limit)
            .to_arrow()
        )

        document_map = {str(document.id): document for document in documents}
        return self._take_sources_up_to_max_tokens(
            (
                Source(
                    id=result["id"],
                    document=document_map[result["document_id"]],
                    # For some reason adding an empty string during store() results
                    # in this field being None. Thus, we need to parse it back here.
                    # TODO: See if there is a configuration option for this
                    location=result["page_numbers"] or "",
                    content=result["text"],
                    num_tokens=result["num_tokens"],
                )
                for result in results.to_pylist()
            ),
            max_tokens=num_tokens,
        )
