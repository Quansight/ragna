import functools
import textwrap
import uuid
from typing import Any

from ragna.core import (
    Document,
    MetadataFilter,
    MetadataOperator,
    RagnaException,
    Source,
    SourceStorage,
)


class RagnaDemoSourceStorage(SourceStorage):
    """Demo assistant without requirements.

    !!! note

        As the name implies, this source storage is just for demo purposes and cannot
        retrieve relevant sources for a given prompt. It returns a single
        [ragna.core.Source][] per stored [ragna.core.Document][] with potentially
        shortened text extracted from the first [ragna.core.Page][].
    """

    @classmethod
    def display_name(cls) -> str:
        return "Ragna/DemoSourceStorage"

    def __init__(self) -> None:
        self._storage: list[dict[str, Any]] = []

    def store(self, documents: list[Document]) -> None:
        self._storage.extend(
            [
                dict(
                    document_id=document.id,
                    document_name=document.name,
                    **document.metadata,
                    __id__=str(uuid.uuid4()),
                    __location__=(
                        f"page {page.number}"
                        if (page := next(document.extract_pages())).number
                        else ""
                    ),
                    __content__=(content := textwrap.shorten(page.text, width=100)),
                    __num_tokens__=len(content.split()),
                )
                for document in documents
            ]
        )

    _METADATA_OPERATOR_MAP = {
        MetadataOperator.EQ: lambda a, b: a == b,
        MetadataOperator.NE: lambda a, b: a != b,
        MetadataOperator.LT: lambda a, b: a < b,
        MetadataOperator.LE: lambda a, b: a <= b,
        MetadataOperator.GT: lambda a, b: a > b,
        MetadataOperator.GE: lambda a, b: a >= b,
        MetadataOperator.IN: lambda a, b: a in b,
        MetadataOperator.NOT_IN: lambda a, b: a not in b,
    }

    def _apply_filter(
        self, metadata_filter: MetadataFilter
    ) -> list[tuple[int, dict[str, Any]]]:
        if metadata_filter.operator is MetadataOperator.RAW:
            raise RagnaException
        elif metadata_filter.operator in {MetadataOperator.AND, MetadataOperator.OR}:
            idcs_groups = []
            rows_map = {}
            for child in metadata_filter.value:
                idcs_group = set()
                for idx, row in self._apply_filter(child):
                    idcs_group.add(idx)
                    if idx not in rows_map:
                        rows_map[idx] = row
                idcs_groups.append(idcs_group)
            idcs = functools.reduce(
                (
                    set.intersection
                    if metadata_filter.operator is MetadataOperator.AND
                    else set.union
                ),
                idcs_groups,
            )
            return [(idx, rows_map[idx]) for idx in sorted(idcs)]
        else:
            rows_with_idx = []
            for idx, row in enumerate(self._storage):
                value = row.get(metadata_filter.key)
                if value is None:
                    continue

                if self._METADATA_OPERATOR_MAP[metadata_filter.operator](
                    value, metadata_filter.value
                ):
                    rows_with_idx.append((idx, row))

            return rows_with_idx

    def retrieve(self, metadata_filter: MetadataFilter, prompt: str) -> list[Source]:
        return [
            Source(
                id=row["__id__"],
                document_id=row["document_id"],
                document_name=row["document_name"],
                location=row["__location__"],
                content=row["__content__"],
                num_tokens=row["__num_tokens__"],
            )
            for _, row in self._apply_filter(metadata_filter)
        ]
