import uuid

import ragna
from ragna.core import (
    Document,
    Source,
)

from ._vector_database import VectorDatabaseSourceStorage
from ._embedding import Embedding


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
        self._tokens = 0
        self._embeddings = 0

    def store(
        self,
        documents: list[Embedding],
        *,
        chat_id: uuid.UUID,
    ) -> None:
        collection = self._client.create_collection(
            str(chat_id)
        )

        ids = []
        texts = []
        metadatas = []
        embeddings = []
        for embedding in documents:
            self._tokens += embedding.chunk.num_tokens
            self._embeddings += 1

            ids.append(str(uuid.uuid4()))
            texts.append(embedding.chunk.text)
            metadatas.append(
                {
                    "document_id": str(embedding.chunk.document_id),
                    "page_numbers": self._page_numbers_to_str(embedding.chunk.page_numbers),
                    "num_tokens": embedding.chunk.num_tokens,
                }
            )
            embeddings.append(embedding.embedding)

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,  # type: ignore[arg-type]
        )

    def retrieve(
        self,
        documents: list[Document],
        prompt: list[float],
        *,
        chat_id: uuid.UUID,
        chunk_size: int = 500,
        num_tokens: int = 1024,
    ) -> list[Source]:
        collection = self._client.get_collection(
            str(chat_id)
        )

        result = collection.query(
            query_embeddings=prompt,
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
                max(int(num_tokens * 2 / self._tokens * self._embeddings), 100),
                collection.count(),
            ),
            include=["distances", "metadatas", "documents"],
        )

        num_results = len(result["ids"][0])
        result = {
            key: [None] * num_results if value is None else value[0]  # type: ignore[index]
            for key, value in result.items()
        }
        # dict of lists -> list of dicts
        results = [
            {key[:-1]: value[idx] for key, value in result.items()}
            for idx in range(num_results)
        ]

        # That should be the default, but let's make extra sure here
        results = sorted(results, key=lambda r: r["distance"])

        # TODO: we should have some functionality here to remove results with a high
        #  distance to keep only "valid" sources. However, there are two issues:
        #  1. A "high distance" is fairly subjective
        #  2. Whatever threshold we use is very much dependent on the encoding method
        #  Thus, we likely need to have a callable parameter for this class

        document_map = {str(document.id): document for document in documents}
        return self._take_sources_up_to_max_tokens(
            (
                Source(
                    id=result["id"],
                    document=document_map[result["metadata"]["document_id"]],
                    location=result["metadata"]["page_numbers"],
                    content=result["document"],
                    num_tokens=result["metadata"]["num_tokens"],
                )
                for result in results
            ),
            max_tokens=num_tokens,
        )
