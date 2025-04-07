from __future__ import annotations

import uuid
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Optional, cast

import ragna
from ragna.core import Document, MetadataFilter, MetadataOperator, Source

from ._utils import raise_no_corpuses_available, raise_non_existing_corpus
from ._vector_database import VectorDatabaseSourceStorage

if TYPE_CHECKING:
    import chromadb


class Chroma(VectorDatabaseSourceStorage):
    """[Chroma vector database](https://www.trychroma.com/)

    !!! info "Required packages"

        - `chromadb>=1.0.0`

    !!! warning

        The `NE` and `NOT_IN` metadata filter operators behave differently in Chroma
        than the other builtin source storages. With most other source storages,
        given a key-value pair `(key, value)`, the operators `NE` and `NOT_IN` return
        only the sources with a metadata key `key` and a value not equal to or
        not in, respectively, `value`. To contrast, the `NE` and `NOT_IN` metadata filter
        operators in `ChromaDB` return everything described in the preceding sentence,
        together with all sources that do not have the metadata key `key`.

        For more information, see the notes for `v0.5.12` in the
        [`ChromaDB` migration guide](https://docs.trychroma.com/production/administration/migration).
    """

    # Note that this class has no extra requirements, since the chromadb package is
    # already required for the base class.

    def __init__(self) -> None:
        super().__init__()

        import chromadb

        self._client = chromadb.Client(
            chromadb.config.Settings(
                is_persistent=True,
                persist_directory=str(ragna.local_root() / "chroma"),
                anonymized_telemetry=False,
            )
        )

    def list_corpuses(self) -> list[str]:
        return [c.name for c in self._client.list_collections()]

    def _get_collection(
        self, corpus_name: str, *, create: bool = False
    ) -> chromadb.Collection:
        if create:
            return self._client.get_or_create_collection(
                corpus_name, embedding_function=self._embedding_function
            )

        corpuses = self.list_corpuses()
        if not corpuses:
            raise_no_corpuses_available(self)

        try:
            return self._client.get_collection(
                name=next(name for name in corpuses if name == corpus_name),
                embedding_function=self._embedding_function,
            )
        except StopIteration:
            raise_non_existing_corpus(self, corpus_name)

    def list_metadata(
        self, corpus_name: Optional[str] = None
    ) -> dict[str, dict[str, tuple[str, list[Any]]]]:
        if corpus_name is None:
            corpus_names = self.list_corpuses()
        else:
            corpus_names = [corpus_name]

        metadata = {}
        for corpus_name in corpus_names:
            collection = self._get_collection(corpus_name)

            corpus_metadata = defaultdict(set)
            for row in cast(
                dict[str, list[Any]],
                collection.get(include=["metadatas"]),
            )["metadatas"]:
                for key, value in row.items():
                    if (key.startswith("__") and key.endswith("__")) or value is None:
                        continue

                    corpus_metadata[key].add(value)

            metadata[corpus_name] = {
                key: ({type(value).__name__ for value in values}.pop(), sorted(values))
                for key, values in corpus_metadata.items()
            }

        return metadata

    def store(
        self,
        corpus_name: str,
        documents: list[Document],
        *,
        chunk_size: int = 500,
        chunk_overlap: int = 250,
    ) -> None:
        collection = self._get_collection(corpus_name=corpus_name, create=True)

        ids = []
        texts = []
        metadatas = []
        for document in documents:
            for chunk in self._chunk_pages(
                document.extract_pages(),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            ):
                ids.append(str(uuid.uuid4()))
                texts.append(chunk.text)
                metadatas.append(
                    {
                        "document_id": str(document.id),
                        "document_name": document.name,
                        **document.metadata,
                        "__page_numbers__": self._page_numbers_to_str(
                            chunk.page_numbers
                        ),
                        "__num_tokens__": chunk.num_tokens,
                    }
                )

        collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,  # type: ignore[arg-type]
        )

    # https://docs.trychroma.com/guides#using-where-filters
    _METADATA_OPERATOR_MAP = {
        MetadataOperator.AND: "$and",
        MetadataOperator.OR: "$or",
        MetadataOperator.EQ: "$eq",
        MetadataOperator.NE: "$ne",
        MetadataOperator.LT: "$lt",
        MetadataOperator.LE: "$lte",
        MetadataOperator.GT: "$gt",
        MetadataOperator.GE: "$gte",
        MetadataOperator.IN: "$in",
        MetadataOperator.NOT_IN: "$nin",
    }

    def _translate_metadata_filter(
        self, metadata_filter: Optional[MetadataFilter]
    ) -> Optional[dict[str, Any]]:
        if metadata_filter is None:
            return None
        elif metadata_filter.operator is MetadataOperator.RAW:
            return cast(dict[str, Any], metadata_filter.value)
        elif metadata_filter.operator in {MetadataOperator.AND, MetadataOperator.OR}:
            child_filters = [
                self._translate_metadata_filter(child)
                for child in metadata_filter.value
            ]
            if len(child_filters) > 1:
                operator = self._METADATA_OPERATOR_MAP[metadata_filter.operator]
                return {operator: child_filters}
            else:
                return child_filters[0]
        else:
            return {
                metadata_filter.key: {
                    self._METADATA_OPERATOR_MAP[
                        metadata_filter.operator
                    ]: metadata_filter.value
                }
            }

    def retrieve(
        self,
        corpus_name: str,
        metadata_filter: Optional[MetadataFilter],
        prompt: str,
        *,
        chunk_size: int = 500,
        num_tokens: int = 1024,
    ) -> list[Source]:
        collection = self._get_collection(corpus_name=corpus_name)

        include = ["distances", "metadatas", "documents"]
        result = collection.query(
            query_texts=prompt,
            where=self._translate_metadata_filter(metadata_filter),
            n_results=min(
                # We cannot retrieve source by a maximum number of tokens. Thus, we
                # estimate how many sources we have to query. We overestimate by a
                # factor of two to avoid retrieving to few sources and needed to query
                # again.
                # ---
                # FIXME: querying only a low number of documents can lead to not finding
                #  the most relevant one.
                #  See https://github.com/chroma-core/chroma/issues/1205 for details.
                #  Instead of just querying more documents here, we should use the
                #  appropriate index parameters when creating the collection. However,
                #  they are undocumented for now.
                max(int(num_tokens * 2 / chunk_size), 100),
                collection.count(),
            ),
            include=include,  # type: ignore[arg-type]
        )

        num_results = len(result["ids"][0])
        result = {key: result[key][0] for key in ["ids", *include]}  # type: ignore[literal-required]
        # dict of lists -> list of dicts
        results = [
            {key: value[idx] for key, value in result.items()}
            for idx in range(num_results)
        ]

        # That should be the default, but let's make extra sure here
        results = sorted(results, key=lambda r: r["distances"])

        # TODO: we should have some functionality here to remove results with a high
        #  distance to keep only "valid" sources. However, there are two issues:
        #  1. A "high distance" is fairly subjective
        #  2. Whatever threshold we use is very much dependent on the encoding method
        #  Thus, we likely need to have a callable parameter for this class

        return self._take_sources_up_to_max_tokens(
            (
                Source(
                    id=result["ids"],
                    document_name=result["metadatas"]["document_name"],
                    document_id=result["metadatas"]["document_id"],
                    location=result["metadatas"]["__page_numbers__"],
                    content=result["documents"],
                    num_tokens=result["metadatas"]["__num_tokens__"],
                )
                for result in results
            ),
            max_tokens=num_tokens,
        )
