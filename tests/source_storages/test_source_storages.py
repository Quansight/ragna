import random
import string
from collections import defaultdict

import pytest

from ragna.core import (
    LocalDocument,
    MetadataFilter,
    PlainTextDocumentHandler,
    RagnaException,
)
from ragna.source_storages import Chroma, LanceDB, RagnaDemoSourceStorage

SOURCE_STORAGES = [Chroma, LanceDB, RagnaDemoSourceStorage]

METADATAS = {
    0: {"key": "value"},
    1: {"key": "value", "other_key": "other_value"},
    2: {"key": "other_value"},
    3: {"other_key": "value"},
    4: {"other_key": "other_value"},
    5: {"key": "foo"},
    6: {"key": "bar"},
}

metadata_filters = pytest.mark.parametrize(
    ("metadata_filter", "expected_idcs"),
    [
        # pytest.param(
        #     MetadataFilter.and_(
        #         [
        #             MetadataFilter.eq("key", "value"),
        #             MetadataFilter.eq("other_key", "other_value"),
        #         ]
        #     ),
        #     [1],
        #     id="and",
        # ),
        # pytest.param(
        #     MetadataFilter.or_(
        #         [
        #             MetadataFilter.eq("key", "value"),
        #             MetadataFilter.eq("key", "other_value"),
        #         ]
        #     ),
        #     [0, 1, 2],
        #     id="or",
        # ),
        # pytest.param(
        #     MetadataFilter.and_(
        #         [
        #             MetadataFilter.eq("key", "value"),
        #             MetadataFilter.or_(
        #                 [
        #                     MetadataFilter.eq("key", "other_value"),
        #                     MetadataFilter.eq("other_key", "other_value"),
        #                 ]
        #             ),
        #         ]
        #     ),
        #     [1],
        #     id="and-nested",
        # ),
        # pytest.param(
        #     MetadataFilter.or_(
        #         [
        #             MetadataFilter.eq("key", "value"),
        #             MetadataFilter.and_(
        #                 [
        #                     MetadataFilter.eq("key", "other_value"),
        #                     MetadataFilter.ne("other_key", "other_value"),
        #                 ]
        #             ),
        #         ]
        #     ),
        #     [0, 1],
        #     id="or-nested",
        # ),
        # pytest.param(
        #     MetadataFilter.and_(
        #         [MetadataFilter.in_("other_key", ["value", "other_value"])]
        #     ),
        #     [1, 3, 4],
        #     id="and-single",
        # ),
        # pytest.param(
        #     MetadataFilter.or_([MetadataFilter.eq("other_key", "other_value")]),
        #     [1, 4],
        #     id="or-single",
        # ),
        # pytest.param(MetadataFilter.eq("key", "value"), [0, 1], id="eq"),
        pytest.param(MetadataFilter.ne("key", "value"), [2, 5, 6], id="ne"),
        # pytest.param(MetadataFilter.in_("key", ["foo", "bar"]), [5, 6], id="in"),
        # pytest.param(
        #     MetadataFilter.not_in("key", ["foo", "bar"]), [0, 1, 2], id="not_in"
        # ),
        # pytest.param(None, [0, 1, 2, 3, 4, 5, 6], id="none"),
    ],
)


@metadata_filters
@pytest.mark.parametrize("source_storage_cls", [Chroma])  # LanceDB
def test_smoke(tmp_local_root, source_storage_cls, metadata_filter, expected_idcs):
    document_root = tmp_local_root / "documents"
    document_root.mkdir()
    documents = []
    for idx, meta_dict in METADATAS.items():
        path = document_root / str(idx)
        with open(path, "w") as file:
            file.write(f"The secret number is {idx}!\n")

        documents.append(
            LocalDocument.from_path(
                path,
                metadata=meta_dict | {"idx": idx},
                handler=PlainTextDocumentHandler(),
            )
        )

    source_storage = source_storage_cls()
    corpus_name = "default"

    source_storage.store(corpus_name, documents)

    prompt = "What is the secret number?"
    num_tokens = 4096
    sources = source_storage.retrieve(
        corpus_name=corpus_name,
        metadata_filter=metadata_filter,
        prompt=prompt,
        num_tokens=num_tokens,
    )

    actual_idcs = sorted(map(int, (source.document_name for source in sources)))
    assert actual_idcs == expected_idcs

    # Should be able to call .store() multiple times
    source_storage.store(corpus_name, documents)


@pytest.mark.parametrize("source_storage_cls", [Chroma, LanceDB])
def test_corpus_names(tmp_local_root, source_storage_cls):
    document_root = tmp_local_root / "documents"
    document_root.mkdir()

    secret_corpus_name = "secret_corpus"
    secret_path = document_root / "secret_doc"
    secret = "42"
    with open(secret_path, "w") as file:
        file.write(f"The secret is {secret}!\n")
    secret_document = LocalDocument.from_path(
        secret_path,
        handler=PlainTextDocumentHandler(),
    )

    dummy_corpus_name = "dummy_corpus"
    dummy_path = document_root / "dummy_doc"
    with open(dummy_path, "w") as file:
        file.write("Dummy Doc!\n")
    dummy_document = LocalDocument.from_path(
        dummy_path,
        handler=PlainTextDocumentHandler(),
    )

    source_storage = source_storage_cls()

    assert source_storage.list_corpuses() == []
    source_storage.store(secret_corpus_name, [secret_document])
    source_storage.store(dummy_corpus_name, [dummy_document])

    assert set(source_storage.list_corpuses()) == {
        dummy_corpus_name,
        secret_corpus_name,
    }

    prompt = "What is the secret number?"
    num_tokens = 4096

    secret_sources = source_storage.retrieve(
        corpus_name=secret_corpus_name,
        prompt=prompt,
        metadata_filter=None,
        num_tokens=num_tokens,
    )
    assert secret in secret_sources[0].content

    dummy_sources = source_storage.retrieve(
        corpus_name=dummy_corpus_name,
        prompt=prompt,
        metadata_filter=None,
        num_tokens=num_tokens,
    )
    assert secret not in dummy_sources[0].content


@pytest.mark.parametrize("cls", SOURCE_STORAGES)
def test_no_corpuses_error(tmp_local_root, cls):
    source_storage = cls()

    raises_error = pytest.raises(RagnaException, match="No corpuses available")

    with raises_error:
        source_storage.list_metadata(corpus_name="")

    with raises_error:
        source_storage.retrieve(corpus_name="", metadata_filter=None, prompt="")


@pytest.mark.parametrize("cls", SOURCE_STORAGES)
def test_non_existing_corpus_error(tmp_local_root, cls):
    document_root = tmp_local_root / "documents"
    document_root.mkdir()

    document_path = document_root / "document.txt"
    with open(document_path, "w") as file:
        file.write("!")
    document = LocalDocument.from_path(document_path)

    source_storage = cls()
    source_storage.store(corpus_name="default", documents=[document])

    unknown_corpus_name = "unknown"
    raises_error = pytest.raises(RagnaException, match="Corpus does not exist")

    with raises_error:
        source_storage.list_metadata(corpus_name=unknown_corpus_name)

    with raises_error:
        source_storage.retrieve(
            corpus_name=unknown_corpus_name, metadata_filter=None, prompt=""
        )


@pytest.mark.parametrize("cls", SOURCE_STORAGES)
def test_list_metadata(tmp_local_root, cls):
    document_root = tmp_local_root / "documents"
    document_root.mkdir()

    documents = []
    for idx in range(5):
        path = (document_root / f"document{idx}").with_suffix(
            random.choice([".txt", ".md"])
        )
        with open(path, "w") as file:
            file.write(
                "".join(random.choices(string.ascii_letters, k=random.randint(1, 10)))
            )
        documents.append(LocalDocument.from_path(path))

    corpuses = {
        "corpus0": documents[: len(documents) // 2],
        "corpus1": documents[len(documents) // 2 :],
    }

    source_storage = cls()
    expected_metadata = {}
    for corpus_name, documents in corpuses.items():
        source_storage.store(corpus_name, documents)

        corpus_metadata = defaultdict(set)
        for document in documents:
            corpus_metadata["document_id"].add(str(document.id))
            corpus_metadata["document_name"].add(document.name)
            for key, value in document.metadata.items():
                corpus_metadata[key].add(value)

        expected_metadata[corpus_name] = {
            key: ({type(value).__name__ for value in values}.pop(), values)
            for key, values in corpus_metadata.items()
        }

    # We don't impose an order of the available values so we turn them into a set
    actual_metadata = {
        corpus_name: {
            key: (type_, set(values)) for key, (type_, values) in metadata.items()
        }
        for corpus_name, metadata in source_storage.list_metadata().items()
    }

    assert actual_metadata == expected_metadata
