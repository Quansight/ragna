from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Optional, cast

import ragna
from ragna.core import Document, MetadataFilter, MetadataOperator, Source

from ._vector_database import VectorDatabaseSourceStorage

if TYPE_CHECKING:
    import chromadb


class Chroma(VectorDatabaseSourceStorage):
    """[Chroma vector database](https://www.trychroma.com/)

    !!! info "Required packages"

        - `chromadb>=0.4.13`
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

    def _get_collection(self, corpus_name: Optional[str]) -> chromadb.Collection:
        if corpus_name is None:
            corpus_name = self._embedding_id

        return self._client.get_or_create_collection(
            corpus_name, embedding_function=self._embedding_function
        )

    def store(
        self,
        corpus_name: Optional[str],
        documents: list[Document],
        *,
        chunk_size: int = 500,
        chunk_overlap: int = 250,
    ) -> None:
        collection = self._get_collection(corpus_name=corpus_name)

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
                        "page_numbers": self._page_numbers_to_str(chunk.page_numbers),
                        "num_tokens": chunk.num_tokens,
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
        corpus_name: Optional[str],
        metadata_filter: MetadataFilter,
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
                    location=result["metadatas"]["page_numbers"],
                    content=result["documents"],
                    num_tokens=result["metadatas"]["num_tokens"],
                )
                for result in results
            ),
            max_tokens=num_tokens,
        )
