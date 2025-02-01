import contextlib

from ragna.deploy import Config
from tests.deploy.utils import make_api_client


def test_get_documents(tmp_local_root):
    config = Config(local_root=tmp_local_root)

    needs_more_of = ["reverb", "cowbell"]

    document_root = config.local_root / "documents"
    document_root.mkdir()
    document_paths = [
        document_root / f"test{counter}.txt" for counter in range(len(needs_more_of))
    ]
    for what_it_needs, document_path in zip(needs_more_of, document_paths):
        with open(document_path, "w") as file:
            file.write(f"Needs more {what_it_needs}\n")

    with make_api_client(
        config=Config(), ignore_unavailable_components=False
    ) as client:
        documents = (
            client.post(
                "/api/documents",
                json=[{"name": document_path.name} for document_path in document_paths],
            )
            .raise_for_status()
            .json()
        )

        with contextlib.ExitStack() as stack:
            files = [
                stack.enter_context(open(document_path, "rb"))
                for document_path in document_paths
            ]
            client.put(
                "/api/documents",
                files=[
                    ("documents", (document["id"], file))
                    for document, file in zip(documents, files)
                ],
            )

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
        file.write("Needs more reverb\n")

    with make_api_client(
        config=Config(), ignore_unavailable_components=False
    ) as client:
        document = (
            client.post(
                "/api/documents",
                json=[{"name": document_path.name}],
            )
            .raise_for_status()
            .json()[0]
        )

        with open(document_path, "rb") as file:
            client.put(
                "/api/documents",
                files=[("documents", (document["id"], file))],
            )

        response = client.get(f"/api/documents/{document['id']}").raise_for_status()

        assert document == response.json()


def test_get_document_content(tmp_local_root):
    config = Config(local_root=tmp_local_root)

    document_root = config.local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("Needs more reverb\n")

    with make_api_client(
        config=Config(), ignore_unavailable_components=False
    ) as client:
        document = (
            client.post(
                "/api/documents",
                json=[{"name": document_path.name}],
            )
            .raise_for_status()
            .json()[0]
        )

        with open(document_path, "rb") as file:
            client.put(
                "/api/documents",
                files=[("documents", (document["id"], file))],
            )

        with client.stream(
            "GET", f"/api/documents/{document['id']}/content"
        ) as response:
            received_lines = list(response.iter_lines())

        assert received_lines == ["Needs more reverb"]
