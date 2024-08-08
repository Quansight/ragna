import pytest

from ragna.core import LocalDocument, MetadataFilter, PlainTextDocumentHandler
from ragna.source_storages import Chroma, LanceDB

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
        pytest.param(
            MetadataFilter.and_(
                [
                    MetadataFilter.eq("key", "value"),
                    MetadataFilter.eq("other_key", "other_value"),
                ]
            ),
            [1],
            id="and",
        ),
        pytest.param(
            MetadataFilter.or_(
                [
                    MetadataFilter.eq("key", "value"),
                    MetadataFilter.eq("key", "other_value"),
                ]
            ),
            [0, 1, 2],
            id="or",
        ),
        pytest.param(
            MetadataFilter.and_(
                [
                    MetadataFilter.eq("key", "value"),
                    MetadataFilter.or_(
                        [
                            MetadataFilter.eq("key", "other_value"),
                            MetadataFilter.eq("other_key", "other_value"),
                        ]
                    ),
                ]
            ),
            [1],
            id="and-nested",
        ),
        pytest.param(
            MetadataFilter.or_(
                [
                    MetadataFilter.eq("key", "value"),
                    MetadataFilter.and_(
                        [
                            MetadataFilter.eq("key", "other_value"),
                            MetadataFilter.ne("other_key", "other_value"),
                        ]
                    ),
                ]
            ),
            [0, 1],
            id="or-nested",
        ),
        pytest.param(MetadataFilter.eq("key", "value"), [0, 1], id="eq"),
        pytest.param(MetadataFilter.ne("key", "value"), [2, 5, 6], id="ne"),
        pytest.param(MetadataFilter.in_("key", ["foo", "bar"]), [5, 6], id="in"),
        pytest.param(
            MetadataFilter.not_in("key", ["foo", "bar"]), [0, 1, 2], id="not_in"
        ),
        pytest.param(None, [0, 1, 2, 3, 4, 5, 6], id="none"),
    ],
)


@metadata_filters
@pytest.mark.parametrize("source_storage_cls", [Chroma, LanceDB])
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
    source_storage.store(documents)

    prompt = "What is the secret number?"
    num_tokens = 4096
    sources = source_storage.retrieve(
        metadata_filter=metadata_filter, prompt=prompt, num_tokens=num_tokens
    )

    actual_idcs = sorted(map(int, (source.document_name for source in sources)))
    assert actual_idcs == expected_idcs

    # Should be able to call .store() multiple times
    source_storage.store(documents)
