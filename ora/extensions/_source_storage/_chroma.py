import functools
import hashlib

from ora.extensions import (
    Document,
    hookimpl,
    PackageRequirement,
    Requirement,
    Source,
    SourceStorage,
)
from ora.utils import chunk_pages, page_numbers_to_str


class ChromaSourceStorage(SourceStorage):
    @classmethod
    def display_name(cls) -> str:
        return "Chroma"

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("chromadb >=0.4")]

    def __init__(self, app_config, embedding_function=None, tokenizer=None):
        super().__init__(app_config)
        import chromadb
        import chromadb.utils.embedding_functions

        # FIXME: pull cache path from app_config
        self._client = chromadb.Client(
            chromadb.config.Settings(anonymized_telemetry=False)
        )

        # FIXME use a free one here
        self._embedding_function = (
            embedding_function
            or chromadb.utils.embedding_functions.OpenAIEmbeddingFunction()
        )
        self._tokenizer = tokenizer

    @functools.lru_cache(maxsize=1024)
    def _collection_name(self, user_name: str) -> str:
        return hashlib.md5(user_name.encode()).hexdigest()

    def _extract_chunk_params(self, chat_config) -> tuple[int, int]:
        chunk_size = chat_config.extra.get("chunk_size", 500)
        chunk_overlap = chat_config.extra.get("chunk_overlap", 250)
        return chunk_size, chunk_overlap

    def store(self, documents: list[Document], chat_config) -> None:
        collection = self._client.get_or_create_collection(
            self._collection_name(self.app_config.user_name)
        )

        chunk_size, chunk_overlap = self._extract_chunk_params(chat_config)

        ids_to_store: list[str] = []
        documents_to_store: list[str] = []
        metadatas_to_store: list[dict[str, str]] = []
        for document in documents:
            # check if we already have documents with id and chunking in the collection
            # if so, continue
            if False:
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
                    hashlib.md5(
                        f"{document.name}--{chunk_size}--{chunk_overlap}--{idx}".encode()
                    ).hexdigest()
                )
                documents_to_store.append(chunk.text)
                metadatas_to_store.append(
                    {
                        "doc_name": document.name,
                        "doc_id": document.id,
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
            self._collection_name(self.app_config.user_name)
        )

        chunk_size, _ = self._extract_chunk_params(chat_config)
        results = collection.query(
            query_texts=prompt,
            n_results=min(
                # We cannot retrieve source by a maximum number of tokens. Thus, we
                # estimate how many sources we have to query. We overestimate by a
                # factor of two to avoid retrieving to few sources and needed to query
                # again.
                int(num_tokens * 2 / chunk_size),
                collection.count(),
            ),
            # filter based on doc id from chat config here
        )
        # Chroma results come as dict of lists, but we need list of dicts here

        # sort them by distance ascending. I think they are already sorted, but let's
        # make sure

        # FIXME: implement culling here based on distance

        # Limit number of tokens
        return [
            Source(
                name=result["metadatas"]["doc_name"],
                location=result["metadatas"]["page_numbers"],
                text=result["documents"],
            )
            for result in results
        ]


@hookimpl(specname="ora_source_storage")
def chroma_source_storage():
    return ChromaSourceStorage
