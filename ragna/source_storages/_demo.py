import functools
import textwrap
import uuid
from collections import defaultdict
from typing import Any, Callable, Optional, cast

from ragna.core import (
    Document,
    MetadataFilter,
    MetadataOperator,
    RagnaException,
    Source,
    SourceStorage,
)

from ._utils import raise_no_corpuses_available, raise_non_existing_corpus


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
        self._storage: dict[str, list[dict[str, Any]]] = {}

    def list_corpuses(self) -> list[str]:
        return list(self._storage.keys())

    def _get_corpus(
        self, corpus_name: str, *, create: bool = False
    ) -> list[dict[str, Any]]:
        if create:
            return self._storage.setdefault(corpus_name, [])

        if not self._storage:
            raise_no_corpuses_available(self)

        corpus = self._storage.get(corpus_name)
        if corpus is None:
            raise_non_existing_corpus(self, corpus_name)

        return corpus

    def list_metadata(
        self, corpus_name: Optional[str] = None
    ) -> dict[str, dict[str, tuple[str, list[Any]]]]:
        if corpus_name is None:
            corpus_names = self.list_corpuses()
        else:
            corpus_names = [corpus_name]

        metadata = {}
        for corpus_name in corpus_names:
            corpus = self._get_corpus(corpus_name)
            corpus_metadata = defaultdict(set)

            for row in corpus:
                for key, value in row.items():
                    if (key.startswith("__") and key.endswith("__")) or value is None:
                        continue

                    corpus_metadata[key].add(value)

            metadata[corpus_name] = {
                key: ({type(value).__name__ for value in values}.pop(), sorted(values))
                for key, values in corpus_metadata.items()
            }

        return metadata

    def store(self, corpus_name: str, documents: list[Document]) -> None:
        corpus = self._get_corpus(corpus_name, create=True)
        # FIXME: handle updating metadata (either introducing new or filling with None)
        #  and add a type check
        corpus.extend(
            [
                dict(
                    document_id=str(document.id),
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

    _METADATA_OPERATOR_MAP: dict[MetadataOperator, Callable[[Any, Any], bool]] = {
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
        self, corpus: list[dict[str, Any]], metadata_filter: Optional[MetadataFilter]
    ) -> list[tuple[int, dict[str, Any]]]:
        if metadata_filter is None:
            return list(enumerate(corpus))
        elif metadata_filter.operator is MetadataOperator.RAW:
            raise RagnaException
        elif metadata_filter.operator in {MetadataOperator.AND, MetadataOperator.OR}:
            idcs_groups = []
            rows_map = {}
            for child in metadata_filter.value:
                idcs_group = set()
                for idx, row in self._apply_filter(corpus, child):
                    idcs_group.add(idx)
                    if idx not in rows_map:
                        rows_map[idx] = row
                idcs_groups.append(idcs_group)
            idcs = functools.reduce(
                cast(
                    Callable[[set[int], set[int]], set[int]],
                    (
                        set.intersection
                        if metadata_filter.operator is MetadataOperator.AND
                        else set.union
                    ),
                ),
                idcs_groups,
            )
            return [(idx, rows_map[idx]) for idx in sorted(idcs)]
        else:
            rows_with_idx = []
            for idx, row in enumerate(corpus):
                value = row.get(metadata_filter.key)
                if value is None:
                    continue

                if self._METADATA_OPERATOR_MAP[metadata_filter.operator](
                    value, metadata_filter.value
                ):
                    rows_with_idx.append((idx, row))

            return rows_with_idx

    def retrieve(
        self, corpus_name: str, metadata_filter: MetadataFilter, prompt: str
    ) -> list[Source]:
        return [
            Source(
                id=row["__id__"],
                document_id=row["document_id"],
                document_name=row["document_name"],
                location=row["__location__"],
                content=row["__content__"],
                num_tokens=row["__num_tokens__"],
            )
            for _, row in self._apply_filter(
                self._get_corpus(corpus_name), metadata_filter
            )
        ]
