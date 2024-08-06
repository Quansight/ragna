import pytest

from ragna.core import LocalDocument, MetadataFilter
from ragna.source_storages import Chroma, LanceDB


@pytest.mark.parametrize(
    "source_storage_cls",
    [
        Chroma,
        # FIXME: remove after LanceDB is fixed
        pytest.param(LanceDB, marks=pytest.mark.xfail()),
    ],
)
def test_smoke(tmp_local_root, source_storage_cls):
    document_root = tmp_local_root / "documents"
    document_root.mkdir()
    documents = []
    for idx in range(10):
        path = document_root / f"irrelevant{idx}.txt"
        with open(path, "w") as file:
            file.write(f"This is irrelevant information for the {idx}. time!\n")

        documents.append(LocalDocument.from_path(path))

    secret = "Ragna"
    path = document_root / "secret.txt"
    with open(path, "w") as file:
        file.write(f"The secret is {secret}!\n")

    documents.insert(len(documents) // 2, LocalDocument.from_path(path))

    source_storage = source_storage_cls()

    source_storage.store(documents)

    metadata_filter = MetadataFilter.or_(
        [MetadataFilter.eq("document_id", str(document.id)) for document in documents]
    )
    prompt = "What is the secret?"
    sources = source_storage.retrieve(metadata_filter, prompt)

    assert secret in sources[0].content
