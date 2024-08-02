import pytest

from ragna.core import LocalDocument, MetadataFilter
from ragna.source_storages import Chroma, LanceDB

METADATAS = [
    {"key": "value"},
    {"key": "value", "other_key": "other_value"},
    {"key": "other_value"},
    {"other_key": "value"},
    {"other_key": "other_value"},
    {"key": "foo"},
    {"key": "bar"},
]

metadata_filters = pytest.mark.parametrize(
    "metadata_filter,n_expected_sources",
    [
        pytest.param(
            MetadataFilter.and_(
                [
                    MetadataFilter.eq("key", "value"),
                    MetadataFilter.eq("other_key", "other_value"),
                ]
            ),
            1,
            id="and",
        ),
        pytest.param(
            MetadataFilter.or_(
                [
                    MetadataFilter.eq("key", "value"),
                    MetadataFilter.eq("key", "other_value"),
                ]
            ),
            3,
            id="or",
        ),
        pytest.param(
            MetadataFilter.and_(
                [
                    MetadataFilter.eq("key", "value"),
                    MetadataFilter.or_(
                        [
                            MetadataFilter.eq("key", "other_value"),
                            MetadataFilter.ne("other_key", "other_value"),
                        ]
                    ),
                ]
            ),
            1,
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
            3,
            id="or-nested",
        ),
        pytest.param(MetadataFilter.eq("key", "value"), 2, id="eq"),
        pytest.param(MetadataFilter.ne("key", "value"), 5, id="ne"),
        pytest.param(MetadataFilter.in_("key", ["foo", "bar"]), 2, id="in"),
        pytest.param(MetadataFilter.not_in("key", ["foo", "bar"]), 5, id="not_in"),
        pytest.param(None, 7, id="none"),
    ],
)


@metadata_filters
@pytest.mark.parametrize("source_storage_cls", [Chroma, LanceDB])
def test_smoke(tmp_local_root, source_storage_cls, metadata_filter, n_expected_sources):
    document_root = tmp_local_root / "documents"
    document_root.mkdir()
    documents = []
    for idx, meta_dict in enumerate(METADATAS):
        path = document_root / f"document{idx}.txt"
        with open(path, "w") as file:
            file.write(f"The secret number is {idx}!\n")

        documents.append(
            LocalDocument.from_path(path, metadata=meta_dict | {"idx": idx})
        )

    source_storage = source_storage_cls()

    source_storage.store(documents)

    prompt = "What is the secret number?"
    num_tokens = 4096
    sources = source_storage.retrieve(
        metadata_filter=metadata_filter, prompt=prompt, num_tokens=num_tokens
    )
    assert len(sources) == n_expected_sources

    # Should be able to call .store() multiple times
    source_storage.store(documents)
