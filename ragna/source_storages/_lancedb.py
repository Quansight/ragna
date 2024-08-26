from __future__ import annotations

import uuid
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Optional, cast

import ragna
from ragna.core import (
    Document,
    MetadataFilter,
    MetadataOperator,
    PackageRequirement,
    RagnaException,
    Requirement,
    Source,
)

from ._utils import raise_no_corpuses_available, raise_non_existing_corpus
from ._vector_database import VectorDatabaseSourceStorage

if TYPE_CHECKING:
    import lancedb


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

    def list_corpuses(self) -> list[str]:
        return list(self._db.table_names())

    _VECTOR_COLUMN_NAME = "__embedded_text__"

    def _get_table(
        self, corpus_name: str, *, create: bool = False
    ) -> lancedb.table.Table:
        table_names = list(self._db.table_names())
        no_corpuses = not table_names
        non_existing_corpus = corpus_name not in table_names

        if (no_corpuses or non_existing_corpus) and create:
            import pyarrow as pa

            return self._db.create_table(
                name=corpus_name,
                schema=pa.schema(
                    [
                        pa.field("__id__", pa.string()),
                        pa.field("document_id", pa.string()),
                        pa.field("document_name", pa.string()),
                        pa.field("__page_numbers__", pa.string()),
                        pa.field("__text__", pa.string()),
                        pa.field(
                            self._VECTOR_COLUMN_NAME,
                            pa.list_(pa.float32(), self._embedding_dimensions),
                        ),
                        pa.field("__num_tokens__", pa.int32()),
                    ]
                ),
            )
        elif no_corpuses:
            raise_no_corpuses_available(self)
        elif non_existing_corpus:
            raise_non_existing_corpus(self, corpus_name)
        else:
            return self._db.open_table(corpus_name)

    def list_metadata(
        self, corpus_name: Optional[str] = None
    ) -> dict[str, dict[str, tuple[str, list[Any]]]]:
        if corpus_name is None:
            corpus_names = self.list_corpuses()
        else:
            corpus_names = [corpus_name]

        metadata = {}
        for corpus_name in corpus_names:
            table = self._get_table(corpus_name)
            corpus_metadata = (
                table.to_arrow()
                .select(
                    [
                        key
                        for key in table.schema.names
                        if not (key.startswith("__") and key.endswith("__"))
                    ]
                )
                .to_pydict()
            )
            corpus_metadata = {
                key: set(values) for key, values in corpus_metadata.items()
            }

            metadata[corpus_name] = {
                key: (
                    {type(value).__name__ for value in values}.pop(),
                    sorted(values),
                )
                for key, values in corpus_metadata.items()
            }

        return metadata

    _PYTHON_TO_LANCE_TYPE_MAP = {
        bool: "boolean",
        int: "int",
        float: "float",
        str: "string",
    }

    def store(
        self,
        corpus_name: str,
        documents: list[Document],
        *,
        chunk_size: int = 500,
        chunk_overlap: int = 250,
    ) -> None:
        table = self._get_table(corpus_name, create=True)

        document_field_types = defaultdict(set)
        for document in documents:
            for field, value in document.metadata.items():
                document_field_types[field].add(type(value))

        document_fields = {}
        for field, types in document_field_types.items():
            if len(types) > 1:
                raise RagnaException(
                    "Multiple types for metadata value", key=field, types=sorted(types)
                )
            document_fields[field] = self._PYTHON_TO_LANCE_TYPE_MAP[types.pop()]

        schema_fields = set(table.schema.names)

        missing_fields = document_fields.keys() - schema_fields
        if missing_fields:
            # Unfortunately, LanceDB does not support adding columns with a specific
            # type, but the the type is automatically inferred from the value.
            table.add_columns(
                {
                    field: f"CAST(NULL as {document_fields[field]})"
                    for field in missing_fields
                }
            )

        default_metadata = {
            field: None for field in document_fields.keys() | schema_fields
        }

        table.add(
            [
                {
                    # Unpacking the default metadata first so it can be
                    # overridden by concrete values if present
                    **default_metadata,
                    **document.metadata,
                    "__id__": str(uuid.uuid4()),
                    "document_id": str(document.id),
                    "document_name": str(document.name),
                    "__page_numbers__": self._page_numbers_to_str(chunk.page_numbers),
                    "__text__": chunk.text,
                    self._VECTOR_COLUMN_NAME: self._embedding_function([chunk.text])[0],
                    "__num_tokens__": chunk.num_tokens,
                }
                for document in documents
                for chunk in self._chunk_pages(
                    document.extract_pages(),
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
            ]
        )

    # https://lancedb.github.io/lancedb/sql/
    _METADATA_OPERATOR_MAP = {
        MetadataOperator.AND: "AND",
        MetadataOperator.OR: "OR",
        MetadataOperator.EQ: "=",
        MetadataOperator.NE: "!=",
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
            operator = f" {self._METADATA_OPERATOR_MAP[metadata_filter.operator]} "
            return operator.join(
                f"({self._translate_metadata_filter(child)})"
                for child in metadata_filter.value
            )
        elif metadata_filter.operator is MetadataOperator.NOT_IN:
            in_ = self._translate_metadata_filter(
                MetadataFilter.in_(metadata_filter.key, metadata_filter.value)
            )
            return f"NOT ({in_})"
        else:
            key = metadata_filter.key
            operator = self._METADATA_OPERATOR_MAP[metadata_filter.operator]
            value = (
                tuple(metadata_filter.value)
                if metadata_filter.operator is MetadataOperator.IN
                else metadata_filter.value
            )
            return f"{key} {operator} {value!r}"

    def retrieve(
        self,
        corpus_name: str,
        metadata_filter: Optional[MetadataFilter],
        prompt: str,
        *,
        chunk_size: int = 500,
        num_tokens: int = 1024,
    ) -> list[Source]:
        table = self._get_table(corpus_name)

        # We cannot retrieve source by a maximum number of tokens. Thus, we estimate how
        # many sources we have to query. We overestimate by a factor of two to avoid
        # retrieving too few sources and needing to query again.
        limit = int(num_tokens * 2 / chunk_size)

        search = table.search(
            self._embedding_function([prompt])[0],
            vector_column_name=self._VECTOR_COLUMN_NAME,
        )

        if metadata_filter:
            search = search.where(
                self._translate_metadata_filter(metadata_filter), prefilter=True
            )

        results = search.limit(limit).to_arrow()

        return self._take_sources_up_to_max_tokens(
            (
                Source(
                    id=result["__id__"],
                    document_id=result["document_id"],
                    document_name=result["document_name"],
                    # For some reason adding an empty string during store() results
                    # in this field being None. Thus, we need to parse it back here.
                    # TODO: See if there is a configuration option for this
                    location=result["__page_numbers__"] or "",
                    content=result["__text__"],
                    num_tokens=result["__num_tokens__"],
                )
                for result in results.to_pylist()
            ),
            max_tokens=num_tokens,
        )
