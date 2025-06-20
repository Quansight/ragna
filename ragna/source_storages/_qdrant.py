from __future__ import annotations

import asyncio
import os
import uuid
from collections import defaultdict
from typing import TYPE_CHECKING, Any, AsyncIterator, Optional, cast

import ragna
from ragna.core import (
    Document,
    MetadataFilter,
    MetadataOperator,
    PackageRequirement,
    Requirement,
    Source,
)

from ._utils import raise_no_corpuses_available, raise_non_existing_corpus
from ._vector_database import VectorDatabaseSourceStorage

if TYPE_CHECKING:
    from qdrant_client import models


class Qdrant(VectorDatabaseSourceStorage):
    """[Qdrant vector database](https://qdrant.tech/)

    !!! info

        To connect to a Qdrant server instead of using a local database, use the
        `QDRANT_URL` and `QDRANT_API_KEY` environment variables. For example

        ```shell
        $ export QDRANT_URL="https://xyz-example.eu-central.aws.cloud.qdrant.io:6333"
        $ export QDRANT_API_KEY="<your-api-key-here>"
        ```

    !!! info "Required packages"

        - `qdrant-client>=1.12.0`
    """

    DOC_CONTENT_KEY = "__document"

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            *super().requirements(),
            PackageRequirement("qdrant-client>=1.12.1"),
        ]

    def __init__(self) -> None:
        super().__init__()

        from qdrant_client import AsyncQdrantClient

        if (url := os.environ.get("QDRANT_URL")) is not None:
            kwargs = {"url": url, "api_key": os.environ.get("QDRANT_API_KEY")}
        else:
            kwargs = {"path": str(ragna.local_root() / "qdrant")}
        self._client = AsyncQdrantClient(**kwargs)  # type: ignore[arg-type]

    async def list_corpuses(self) -> list[str]:
        return [c.name for c in (await self._client.get_collections()).collections]

    async def _ensure_table(self, corpus_name: str, *, create: bool = False) -> None:
        table_names = await self.list_corpuses()
        no_corpuses = not table_names
        non_existing_corpus = corpus_name not in table_names

        if non_existing_corpus and create:
            from qdrant_client import models

            await self._client.create_collection(
                collection_name=corpus_name,
                vectors_config=models.VectorParams(
                    size=self._embedding_dimensions, distance=models.Distance.COSINE
                ),
            )
        elif no_corpuses:
            raise_no_corpuses_available(self)
        elif non_existing_corpus:
            raise_non_existing_corpus(self, corpus_name)

    async def _fetch_raw_metadata_entries(
        self, *, corpus_name: str
    ) -> AsyncIterator[dict[str, Any]]:
        ids: list[str] = []
        offset = None
        while True:
            records, offset = await self._client.scroll(
                collection_name=corpus_name,
                with_payload=False,
                # This limit is large because we are trying to make only
                # one request. In order to know the offsets, we first need
                # to know the IDs, and this is how we find them.
                limit=10**6,
                offset=offset,
            )
            ids.extend(cast(str, record.id) for record in records)
            if offset is None:
                break

        # This limit is purely heuristic.
        # There is no way to know a priori the size of the metadata, so
        # we just limit ourselves to twenty requests to the database.
        # This can change in the future.
        limit: int = max(len(ids) // 20, 10)

        for result in asyncio.as_completed(
            [
                self._client.scroll(
                    collection_name=corpus_name,
                    with_payload=True,
                    limit=limit,
                    offset=offset,
                )
                for offset in ids[::limit]
            ]
        ):
            records, _ = await result
            for record in records:
                yield cast(dict[str, Any], record.payload)

    async def _fetch_metadata(self, corpus_name: str) -> dict[str, Any]:
        corpus_metadata = defaultdict(set)
        async for point in self._fetch_raw_metadata_entries(corpus_name=corpus_name):
            for key, value in point.items():
                if any(
                    [
                        (key.startswith("__") and key.endswith("__")),
                        key == self.DOC_CONTENT_KEY,
                        not value,
                    ]
                ):
                    continue

                corpus_metadata[key].add(value)

        return {
            key: ({type(value).__name__ for value in values}.pop(), sorted(values))
            for key, values in corpus_metadata.items()
        }

    async def list_metadata(
        self, corpus_name: Optional[str] = None
    ) -> dict[str, dict[str, tuple[str, list[Any]]]]:
        if corpus_name is None:
            corpus_names = await self.list_corpuses()
        else:
            await self._ensure_table(corpus_name)
            corpus_names = [corpus_name]

        return dict(
            zip(
                corpus_names,
                await asyncio.gather(
                    *[self._fetch_metadata(corpus_name) for corpus_name in corpus_names]
                ),
                strict=False,
            )
        )

    async def store(
        self,
        corpus_name: str,
        documents: list[Document],
        *,
        chunk_size: int = 500,
        chunk_overlap: int = 250,
    ) -> None:
        from qdrant_client import models

        await self._ensure_table(corpus_name, create=True)

        points = []
        for document in documents:
            for chunk in self._chunk_pages(
                document.extract_pages(),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            ):
                points.append(
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=cast(
                            list[float],
                            self._embedding_function([chunk.text])[0].tolist(),
                        ),
                        payload={
                            "document_id": str(document.id),
                            "document_name": document.name,
                            **document.metadata,
                            "__page_numbers__": self._page_numbers_to_str(
                                chunk.page_numbers
                            ),
                            "__num_tokens__": chunk.num_tokens,
                            self.DOC_CONTENT_KEY: chunk.text,
                        },
                    )
                )

        await self._client.upsert(collection_name=corpus_name, points=points)

    def _build_condition(
        self, operator: MetadataOperator, key: str, value: Any
    ) -> models.FieldCondition:
        from qdrant_client import models

        # See https://qdrant.tech/documentation/concepts/filtering/#range
        if operator == MetadataOperator.EQ:
            return models.FieldCondition(key=key, match=models.MatchValue(value=value))
        if operator == MetadataOperator.LT:
            return models.FieldCondition(key=key, range=models.Range(lt=value))
        if operator == MetadataOperator.LE:
            return models.FieldCondition(key=key, range=models.Range(lte=value))
        if operator == MetadataOperator.GT:
            return models.FieldCondition(key=key, range=models.Range(gt=value))
        if operator == MetadataOperator.GE:
            return models.FieldCondition(key=key, range=models.Range(gte=value))
        if operator == MetadataOperator.IN:
            return models.FieldCondition(key=key, match=models.MatchAny(any=value))
        if operator in {MetadataOperator.NE, MetadataOperator.NOT_IN}:
            except_value = [value] if operator == MetadataOperator.NE else value
            return models.FieldCondition(
                key=key, match=models.MatchExcept(**{"except": except_value})
            )

        raise ValueError(f"Unsupported operator: {operator}")

    def _translate_metadata_filter(
        self, metadata_filter: MetadataFilter
    ) -> models.Filter | models.FieldCondition:
        from qdrant_client import models

        if metadata_filter.operator is MetadataOperator.RAW:
            return cast(models.Filter, metadata_filter.value)
        if metadata_filter.operator == MetadataOperator.AND:
            return models.Filter(
                must=[
                    self._translate_metadata_filter(child)
                    for child in metadata_filter.value
                ]
            )
        if metadata_filter.operator == MetadataOperator.OR:
            return models.Filter(
                should=[
                    self._translate_metadata_filter(child)
                    for child in metadata_filter.value
                ]
            )

        return self._build_condition(
            metadata_filter.operator, metadata_filter.key, metadata_filter.value
        )

    async def retrieve(
        self,
        corpus_name: str,
        metadata_filter: Optional[MetadataFilter],
        prompt: str,
        *,
        chunk_size: int = 500,
        num_tokens: int = 1024,
    ) -> list[Source]:
        from qdrant_client import models

        await self._ensure_table(corpus_name)

        # We cannot retrieve source by a maximum number of tokens. Thus, we estimate how
        # many sources we have to query. We overestimate by a factor of two to avoid
        # retrieving too few sources and needing to query again.
        limit = int(num_tokens * 2 / chunk_size)

        query_vector = self._embedding_function([prompt])[0]

        search_filter = (
            self._translate_metadata_filter(metadata_filter)
            if metadata_filter
            else None
        )
        if isinstance(search_filter, models.FieldCondition):
            search_filter = models.Filter(must=[search_filter])

        points = (
            await self._client.query_points(
                collection_name=corpus_name,
                query=query_vector,
                limit=limit,
                query_filter=search_filter,
                with_payload=True,
            )
        ).points

        return self._take_sources_up_to_max_tokens(
            (
                Source(
                    id=cast(str, point.id),
                    document_id=(payload := cast(dict[str, Any], point.payload))[
                        "document_id"
                    ],
                    document_name=payload["document_name"],
                    location=payload["__page_numbers__"],
                    content=payload[self.DOC_CONTENT_KEY],
                    num_tokens=payload["__num_tokens__"],
                )
                for point in points
            ),
            max_tokens=num_tokens,
        )
