import datetime
import json

import httpx

from ragna.core import MetadataFilter


def main():
    client = httpx.Client(base_url="http://127.0.0.1:31476", timeout=None)
    client.get("/health").raise_for_status()

    ## authentication

    # This only works if Ragna was deployed with ragna.core.NoAuth
    # If that is not the case, login in whatever way is required, grab the API token and
    # use the following instead
    # client.headers["Authorization"] = f"Bearer {api_token}"

    client.get("/login", follow_redirects=True).raise_for_status()

    ## documents

    documents = (
        client.post(
            "/api/documents", json=[{"name": f"document{i}.txt"} for i in range(5)]
        )
        .raise_for_status()
        .json()
    )

    print(json.dumps(documents, indent=2))

    client.put(
        "/api/documents",
        files=[
            ("documents", (document["id"], f"Content of {document['name']}".encode()))
            for document in documents
        ],
    ).raise_for_status()

    ## chat 1

    chat = (
        client.post(
            "/api/chats",
            json={
                "name": f"Chat {datetime.datetime.now():%x %X}",
                "input": [document["id"] for document in documents],
                "source_storage": "Ragna/DemoSourceStorage",
                "assistant": "Ragna/DemoAssistant",
            },
        )
        .raise_for_status()
        .json()
    )

    client.post(f"/api/chats/{chat['id']}/prepare").raise_for_status()
    for _ in range(3):
        client.post(
            f"/api/chats/{chat['id']}/answer",
            json={"prompt": "What is Ragna? Please, I need to know!"},
        ).raise_for_status()

    ## chat 2

    chat = (
        client.post(
            "/api/chats",
            json={
                "name": "Test chat",
                "source_storage": "Ragna/DemoSourceStorage",
                "assistant": "Ragna/DemoAssistant",
            },
        )
        .raise_for_status()
        .json()
    )

    client.post(
        f"/api/chats/{chat['id']}/answer",
        json={"prompt": "Hello!"},
    ).raise_for_status()

    # ## chat 3

    chat = (
        client.post(
            "/api/chats",
            json={
                "name": (
                    "Really long chat name that likely needs to be truncated somehow. "
                    "If you can read this, truncating failed :boom:"
                ),
                "input": MetadataFilter.or_(
                    [
                        MetadataFilter.eq("document_id", document["id"])
                        for document in documents[:2]
                    ]
                ).to_primitive(),
                "source_storage": "Ragna/DemoSourceStorage",
                "assistant": "Ragna/DemoAssistant",
            },
        )
        .raise_for_status()
        .json()
    )

    client.post(
        f"/api/chats/{chat['id']}/answer",
        json={"prompt": "Hello!"},
    ).raise_for_status()

    client.post(
        f"/api/chats/{chat['id']}/answer",
        json={"prompt": "Ok, in that case show me some pretty markdown!"},
    ).raise_for_status()

    chats = client.get("/api/chats").raise_for_status().json()
    print(json.dumps(chats))


if __name__ == "__main__":
    main()
