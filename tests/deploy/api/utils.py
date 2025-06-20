import contextlib


def upload_documents(*, client, document_paths, mime_types=None):
    if mime_types is None:
        mime_types = [None for _ in document_paths]
    else:
        assert len(mime_types) == len(document_paths)
    documents = (
        client.post(
            "/api/documents",
            json=[
                {
                    "name": document_path.name,
                    "mime_type": mime_type,
                }
                for document_path, mime_type in zip(
                    document_paths, mime_types, strict=False
                )
            ],
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
                for document, file in zip(documents, files, strict=False)
            ],
        )

    return documents
