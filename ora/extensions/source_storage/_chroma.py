import enum

from typing import Any, TYPE_CHECKING

from ora.extensions import (
    Document,
    hookimpl,
    PackageRequirement,
    Requirement,
    Source,
    SourceStorage,
)
from ora.utils import chunk_pages, compute_id, page_numbers_to_str

if TYPE_CHECKING:
    import chromadb
    import chromadb.utils.embedding_functions
    import tiktoken


class ChromaResultType(enum.Enum):
    GET = enum.auto()
    QUERY = enum.auto()


class ChromaSourceStorage(SourceStorage):
    @classmethod
    def display_name(cls) -> str:
        return "Chroma"

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("chromadb >=0.4"), PackageRequirement("tiktoken")]

    # This needs to be a class variable to enable sharing it between multiple instances.
    # See https://docs.trychroma.com/usage-guide#initiating-a-persistent-chroma-client
    # for details
    _client: "chromadb.Client | None" = None

    def __init__(
        self,
        app_config,
        embedding_function: "chromadb.utils.embedding_functions.EmbeddingFunction | None" = None,
        tokenizer: "tiktoken.Encoding | None" = None,
    ):
        super().__init__(app_config)
        import chromadb
        import chromadb.utils.embedding_functions
        import tiktoken

        if self._client is None:
            self._client = chromadb.Client(
                chromadb.config.Settings(
                    is_persistent=True,
                    persist_directory=str(app_config.cache_root / "chroma"),
                    anonymized_telemetry=False,
                )
            )

        self._embedding_function = (
            embedding_function
            or chromadb.utils.embedding_functions.DefaultEmbeddingFunction()
        )
        self._tokenizer = tokenizer or tiktoken.get_encoding("cl100k_base")

    def _collection_name(self, user_name: str) -> str:
        return compute_id(user_name)

    def _parse_result(
        self, result: dict[str, list | None], *, result_type: ChromaResultType
    ) -> list[dict[str, Any]]:
        if result_type is ChromaResultType.QUERY:
            result = {
                key: value if value is None else value[0]
                for key, value in result.items()
            }

        # ids are always returned so we can use that as starting point
        num_results = len(result["ids"])
        result = {
            key: [None] * num_results if value is None else value
            for key, value in result.items()
        }
        # dict of lists -> list of dicts
        return [
            {key.rstrip("s"): value[idx] for key, value in result.items()}
            for idx in range(num_results)
        ]

    def _extract_chunk_params(self, chat_config) -> tuple[int, int]:
        chunk_size = chat_config.extra.get("chunk_size", 500)
        chunk_overlap = chat_config.extra.get("chunk_overlap", 250)
        return chunk_size, chunk_overlap

    def store(self, documents: list[Document], chat_config) -> None:
        collection = self._client.get_or_create_collection(
            self._collection_name(self.app_config.user)
        )

        chunk_size, chunk_overlap = self._extract_chunk_params(chat_config)

        ids_to_store: list[str] = []
        documents_to_store: list[str] = []
        metadatas_to_store: list[dict[str, str]] = []
        for document in documents:
            result = collection.get(
                where={
                    "$and": [
                        {"document_id": {"$eq": document.id}},
                        {"chunk_size": {"$eq": chunk_size}},
                        {"chunk_overlap": {"$eq": chunk_overlap}},
                    ]
                },
                limit=1,
                include=["metadatas"],
            )
            if self._parse_result(result, result_type=ChromaResultType.GET):
                continue

            pages = document.extract_pages()

            for idx, chunk in enumerate(
                chunk_pages(
                    pages,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    tokenizer=self._tokenizer,
                )
            ):
                ids_to_store.append(
                    compute_id(document.id, chunk_size, chunk_overlap, idx)
                )
                documents_to_store.append(chunk.text)
                metadatas_to_store.append(
                    {
                        "document_name": document.name,
                        "document_id": document.id,
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap,
                        "num_tokens": chunk.num_tokens,
                        "page_numbers": page_numbers_to_str(chunk.page_numbers),
                    }
                )

        if not ids_to_store:
            return

        collection.add(
            ids=ids_to_store, documents=documents_to_store, metadatas=metadatas_to_store
        )

    def retrieve(self, prompt: str, *, num_tokens: int, chat_config) -> list[Source]:
        collection = self._client.get_collection(
            self._collection_name(self.app_config.user)
        )

        document_id_filters = [
            {"document_id": {"$eq": metadata.id}}
            for metadata in chat_config.document_metadatas
        ]
        if len(document_id_filters) == 1:
            document_id_filter = document_id_filters[0]
        else:
            document_id_filter = {"$or": document_id_filters}

        chunk_size, chunk_overlap = self._extract_chunk_params(chat_config)

        result = collection.query(
            query_texts=prompt,
            n_results=min(
                # We cannot retrieve source by a maximum number of tokens. Thus, we
                # estimate how many sources we have to query. We overestimate by a
                # factor of two to avoid retrieving to few sources and needed to query
                # again.
                int(num_tokens * 2 / chunk_size),
                collection.count(),
            ),
            where={
                "$and": [
                    document_id_filter,
                    {"chunk_size": {"$eq": chunk_size}},
                    {"chunk_overlap": {"$eq": chunk_overlap}},
                ]
            },
        )
        results = self._parse_result(result, result_type=ChromaResultType.QUERY)
        # That should be the default, but let's make extra sure here
        results = sorted(results, key=lambda r: r["distance"])

        # FIXME: implement culling here based on distance
        # FIXME: Limit number of tokens

        return [
            Source(
                name=result["metadata"]["document_name"],
                location=result["metadata"]["page_numbers"],
                text=result["document"],
            )
            for result in results
        ]


@hookimpl(specname="ora_source_storage")
def chroma_source_storage():
    return ChromaSourceStorage
