import uuid
from typing import cast

import ragna
from ragna.core import (
    Document,
    MetadataFilter,
    MetadataOperator,
    PackageRequirement,
    Requirement,
    Source,
)

from ._vector_database import VectorDatabaseSourceStorage


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
        import pyarrow as pa

        self._db = lancedb.connect(ragna.local_root() / "lancedb")
        # Create schema at runtime!
        self._schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("document_id", pa.string()),
                pa.field("page_numbers", pa.string()),
                pa.field("text", pa.string()),
                pa.field(
                    self._VECTOR_COLUMN_NAME,
                    pa.list_(pa.float32(), self._embedding_dimensions),
                ),
                pa.field("num_tokens", pa.int32()),
            ]
        )

    _VECTOR_COLUMN_NAME = "embedded_text"

    def store(
        self,
        documents: list[Document],
        *,
        chunk_size: int = 500,
        chunk_overlap: int = 250,
    ) -> None:
        table = self._db.create_table(name=self._embedding_id, schema=self._schema)

        for document in documents:
            for chunk in self._chunk_pages(
                document.extract_pages(),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            ):
                table.add(
                    [
                        {
                            "id": str(uuid.uuid4()),
                            "document_id": str(document.id),
                            "document_name": str(document.name),
                            "page_numbers": self._page_numbers_to_str(
                                chunk.page_numbers
                            ),
                            "text": chunk.text,
                            self._VECTOR_COLUMN_NAME: self._embedding_function(
                                [chunk.text]
                            )[0],
                            "num_tokens": chunk.num_tokens,
                        }
                    ]
                )

    # https://lancedb.github.io/lancedb/sql/
    _METADATA_OPERATOR_MAP = {
        MetadataOperator.AND: "AND",
        MetadataOperator.OR: "OR",
        MetadataOperator.EQ: "=",
        MetadataOperator.LT: "<",
        MetadataOperator.LE: "<=",
        MetadataOperator.GT: ">",
        MetadataOperator.GE: ">=",
        MetadataOperator.IN: "IN",
    }

    def _translate_metadata_filter(self, metadata_filter: MetadataFilter) -> str:
        if metadata_filter.operator is MetadataOperator.RAW:
            return cast(str, metadata_filter.value)
        elif metadata_filter.operator in {
            MetadataOperator.AND,
            MetadataOperator.OR,
        }:
            return f" {self._METADATA_OPERATOR_MAP[metadata_filter.operator]} ".join(
                f"({self._translate_metadata_filter(child)})"
                for child in metadata_filter.value
            )
        elif metadata_filter.operator is MetadataOperator.NE:
            return f"NOT ({self._translate_metadata_filter(MetadataFilter.eq(metadata_filter.key, metadata_filter.value))})"
        elif metadata_filter.operator is MetadataOperator.NOT_IN:
            return f"NOT ({self._translate_metadata_filter(MetadataFilter.in_(metadata_filter.key, metadata_filter.value))})"
        else:
            value = (
                tuple(metadata_filter.value)
                if metadata_filter.operator is MetadataOperator.IN
                else metadata_filter.value
            )
            return f"{metadata_filter.key} {self._METADATA_OPERATOR_MAP[metadata_filter.operator]} {value!r}"

    def retrieve(
        self,
        documents: list[Document],
        prompt: str,
        *,
        chat_id: uuid.UUID,
        chunk_size: int = 500,
        num_tokens: int = 1024,
    ) -> list[Source]:
        table = self._db.open_table(str(chat_id))

        # We cannot retrieve source by a maximum number of tokens. Thus, we estimate how
        # many sources we have to query. We overestimate by a factor of two to avoid
        # retrieving to few sources and needed to query again.
        limit = int(num_tokens * 2 / chunk_size)
        results = (
            table.search(
                self._embedding_function([prompt])[0],
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
