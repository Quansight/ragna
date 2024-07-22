import functools
import textwrap
import uuid

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
        self._storage: list[Source] = []

    def store(self, documents: list[Document]) -> None:
        self._storage.extend(
            [
                Source(
                    id=str(uuid.uuid4()),
                    document=document,
                    location=(
                        f"page {page.number}"
                        if (page := next(document.extract_pages())).number
                        else ""
                    ),
                    content=(content := textwrap.shorten(page.text, width=100)),
                    num_tokens=len(content.split()),
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
    ) -> list[tuple[int, Source]]:
        if metadata_filter.operator is MetadataOperator.RAW:
            raise RagnaException
        elif metadata_filter.operator in {MetadataOperator.AND, MetadataOperator.OR}:
            return sorted(
                functools.reduce(
                    (
                        set.intersection
                        if metadata_filter.operator is MetadataOperator.AND
                        else set.union
                    ),
                    (set(self._apply_filter(child)) for child in metadata_filter.value),
                ),
                key=lambda source_with_idx: source_with_idx[0],
            )
        else:
            sources_with_idx = []
            for idx, source in enumerate(self._storage):
                if metadata_filter.key == "document_id":
                    value = source.document.id
                elif metadata_filter.key == "document_name":
                    value = source.document.name
                else:
                    value = source.document.metadata.get(metadata_filter.key)
                    if value is None:
                        continue

                if self._METADATA_OPERATOR_MAP[metadata_filter.operator](
                    value, metadata_filter.value
                ):
                    sources_with_idx.append((idx, source))

            return sources_with_idx

    def retrieve(self, metadata_filter: MetadataFilter, prompt: str) -> list[Source]:
        return [source for _, source in self._apply_filter(metadata_filter)]
