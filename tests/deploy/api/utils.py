import contextlib


def upload_documents(*, client, document_paths):
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

    return documents
