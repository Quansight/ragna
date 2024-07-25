import pytest

from ragna.core import LocalDocument, MetadataFilter
from ragna.source_storages import LanceDB

METADATAS = [
    {"key": "value"},
    {"key": "other_value"},
    {"other_key": "value"},
    {"other_key": "other_value"},
    {"key": "foo"},
    {"key": "bar"},
]

metadata_filters = pytest.mark.parametrize(
    "metadata_filter",
    [
        pytest.param(MetadataFilter.raw("raw"), id="raw"),
        pytest.param(
            MetadataFilter.and_(
                [
                    MetadataFilter.raw("raw"),
                    MetadataFilter.eq("key", "value"),
                ]
            ),
            id="and",
        ),
        pytest.param(
            MetadataFilter.or_(
                [
                    MetadataFilter.raw("raw"),
                    MetadataFilter.eq("key", "value"),
                ]
            ),
            id="or",
        ),
        pytest.param(
            MetadataFilter.and_(
                [
                    MetadataFilter.raw("raw"),
                    MetadataFilter.or_(
                        [
                            MetadataFilter.eq("key", "value"),
                            MetadataFilter.ne("other_key", "other_value"),
                        ]
                    ),
                ]
            ),
            id="and-nested",
        ),
        pytest.param(
            MetadataFilter.or_(
                [
                    MetadataFilter.raw("raw"),
                    MetadataFilter.and_(
                        [
                            MetadataFilter.eq("key", "value"),
                            MetadataFilter.ne("other_key", "other_value"),
                        ]
                    ),
                ]
            ),
            id="or-nested",
        ),
        pytest.param(MetadataFilter.eq("key", "value"), id="eq"),
        pytest.param(MetadataFilter.ne("key", "value"), id="ne"),
        pytest.param(MetadataFilter.in_("key", ["foo", "bar"]), id="in"),
        pytest.param(MetadataFilter.not_in("key", ["foo", "bar"]), id="not_in"),
        pytest.param(None, id="none"),
    ],
)


@metadata_filters
# @pytest.mark.parametrize("source_storage_cls", [Chroma, LanceDB])
@pytest.mark.parametrize("source_storage_cls", [LanceDB])
def test_smoke(tmp_local_root, source_storage_cls, metadata_filter, request):
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
    sources = source_storage.retrieve(metadata_filter=metadata_filter, prompt=prompt)
    assert sources

    # assert secret in sources[0].content
