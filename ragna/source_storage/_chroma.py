import uuid

from ragna.core import Document, PackageRequirement, Requirement, Source, SourceStorage

from ragna.utils import chunk_pages, page_numbers_to_str, take_sources_up_to_max_tokens


class ChromaSourceStorage(SourceStorage):
    @classmethod
    def display_name(cls) -> str:
        return "Chroma"

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("chromadb >=0.4"), PackageRequirement("tiktoken")]

    def _client(self):
        import chromadb

        return chromadb.Client(
            chromadb.config.Settings(
                is_persistent=True,
                persist_directory=str(self.config.local_cache_root / "chroma"),
                anonymized_telemetry=False,
            )
        )

    def _embedding_function(self):
        import chromadb.utils.embedding_functions

        return chromadb.utils.embedding_functions.DefaultEmbeddingFunction()

    def _tokenizer(self):
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")

    def store(
        self,
        documents: list[Document],
        *,
        chat_id: str,
        chunk_size: int = 500,
        chunk_overlap: int = 250,
    ) -> None:
        collection = self._client().get_or_create_collection(
            chat_id, embedding_function=self._embedding_function()
        )

        ids = []
        texts = []
        metadatas = []
        for document in documents:
            for chunk in chunk_pages(
                document.extract_pages(),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                tokenizer=self._tokenizer(),
            ):
                ids.append(document.id or str(uuid.uuid4()))
                texts.append(chunk.text)
                metadatas.append(
                    {
                        "document_name": document.name,
                        "page_numbers": page_numbers_to_str(chunk.page_numbers),
                        "num_tokens": chunk.num_tokens,
                    }
                )

        collection.add(ids=ids, documents=texts, metadatas=metadatas)

    def retrieve(
        self,
        prompt: str,
        *,
        num_tokens: int = 1024,
        chat_id: str,
        chunk_size: int = 500,
    ) -> list[Source]:
        collection = self._client().get_collection(
            chat_id, embedding_function=self._embedding_function()
        )

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
            include=["distances", "metadatas", "documents"],
        )

        num_results = len(result["ids"])
        result = {
            key: [None] * num_results if value is None else value[0]
            for key, value in result.items()
        }
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

        return list(
            take_sources_up_to_max_tokens(
                (
                    Source(
                        document_id=result["ids"],
                        document_name=result["metadatas"]["document_name"],
                        location=result["metadatas"]["page_numbers"],
                        content=result["documents"],
                        num_tokens=result["metadatas"]["num_tokens"],
                    )
                    for result in results
                ),
                max_tokens=num_tokens,
            )
        )
