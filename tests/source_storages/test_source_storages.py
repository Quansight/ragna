import itertools
import uuid

import pytest

from ragna.core import Chunk, LocalDocument
from ragna.core._compat import chunk_pages
from ragna.embedding_models import AllMiniLML6v2
from ragna.source_storages import Chroma, LanceDB


@pytest.mark.parametrize("source_storage_cls", [Chroma, LanceDB])
def test_smoke(tmp_local_root, source_storage_cls):
    document_root = tmp_local_root / "documents"
    document_root.mkdir()
    documents = []
    for idx in range(10):
        path = document_root / f"irrelevant{idx}.txt"
        with open(path, "w") as file:
            file.write(f"This is irrelevant information for the {idx}!\n")

        documents.append(LocalDocument.from_path(path))

    secret = "Ragna"
    path = document_root / "secret.txt"
    with open(path, "w") as file:
        file.write(f"The secret is {secret}!\n")

    documents.insert(len(documents) // 2, LocalDocument.from_path(path))

    embedding_model = AllMiniLML6v2()
    embeddings = embedding_model.embed_chunks(
        itertools.chain.from_iterable(
            chunk_pages(
                document.extract_pages(),
                document_id=document.id,
                chunk_size=500,
                chunk_overlap=250,
            )
            for document in documents
        )
    )

    source_storage = source_storage_cls()

    # Hardcoding a chat_id here only works because all tested source storages only
    # require this.
    # TODO: make this more flexible by taking required parameters as part of the
    #  parametrization.
    chat_id = uuid.uuid4()

    source_storage.store(embeddings, chat_id=chat_id)

    prompt = "What is the secret?"
    embedded_prompt = embedding_model.embed_chunks(
        [Chunk(text=prompt, document_id=uuid.uuid4(), page_numbers=[], num_tokens=0)]
    )[0].values
    sources = source_storage.retrieve(documents, embedded_prompt, chat_id=chat_id)

    assert secret in sources[0].content
