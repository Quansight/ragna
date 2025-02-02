from ragna.deploy import Config
from tests.deploy.api.utils import upload_documents
from tests.deploy.utils import make_api_client

_document_content_text = [
    f"Needs more {needs_more_of}\n" for needs_more_of in ["reverb", "cowbell"]
]


def test_get_documents(tmp_local_root):
    config = Config(local_root=tmp_local_root)

    document_root = config.local_root / "documents"
    document_root.mkdir()
    document_paths = [
        document_root / f"test{idx}.txt" for idx in range(len(_document_content_text))
    ]
    for content, document_path in zip(_document_content_text, document_paths):
        with open(document_path, "w") as file:
            file.write(content)

    with make_api_client(config=config, ignore_unavailable_components=False) as client:
        documents = upload_documents(client=client, document_paths=document_paths)
        response = client.get("/api/documents").raise_for_status()

    # Sort the items in case they are retrieved in different orders
    def sorting_key(d):
        return d["id"]

    assert sorted(documents, key=sorting_key) == sorted(
        response.json(), key=sorting_key
    )


def test_get_document(tmp_local_root):
    config = Config(local_root=tmp_local_root)

    document_root = config.local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write(_document_content_text[0])

    with make_api_client(config=config, ignore_unavailable_components=False) as client:
        document = upload_documents(client=client, document_paths=[document_path])[0]
        response = client.get(f"/api/documents/{document['id']}").raise_for_status()

    assert document == response.json()


def test_get_document_content(tmp_local_root):
    config = Config(local_root=tmp_local_root)

    document_root = config.local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    document_content = _document_content_text[0]
    with open(document_path, "w") as file:
        file.write(document_content)

    with make_api_client(config=config, ignore_unavailable_components=False) as client:
        document = upload_documents(client=client, document_paths=[document_path])[0]

        with client.stream(
            "GET", f"/api/documents/{document['id']}/content"
        ) as response:
            received_lines = list(response.iter_lines())

    assert received_lines == [document_content.replace("\n", "")]
