import datetime
import json

import httpx


def main():
    client = httpx.Client(base_url="http://127.0.0.1:31476")
    client.get("/").raise_for_status()

    ## authentication

    username = "foo"
    token = (
        client.post(
            "/token",
            data={
                "username": username,
                "password": username,
            },
        )
        .raise_for_status()
        .json()
    )
    client.headers["Authorization"] = f"Bearer {token}"

    ## documents

    documents = []
    for i in range(5):
        name = f"document{i}.txt"
        document_upload = (
            client.post("/document", json={"name": name}).raise_for_status().json()
        )
        parameters = document_upload["parameters"]
        client.request(
            parameters["method"],
            parameters["url"],
            data=parameters["data"],
            files={"file": f"Content of {name}".encode()},
        ).raise_for_status()
        documents.append(document_upload["document"])

    ## chat 1

    chat = (
        client.post(
            "/chats",
            json={
                "name": "Test chat",
                "documents": documents[:2],
                "source_storage": "Ragna/DemoSourceStorage",
                "assistant": "Ragna/DemoAssistant",
                "params": {},
            },
        )
        .raise_for_status()
        .json()
    )

    client.post(f"/chats/{chat['id']}/prepare").raise_for_status()
    client.post(
        f"/chats/{chat['id']}/answer",
        params={"prompt": "Hello!"},
    ).raise_for_status()

    ## chat 2

    chat = (
        client.post(
            "/chats",
            json={
                "name": f"Chat {datetime.datetime.now():%x %X}",
                "documents": documents[2:4],
                "source_storage": "Ragna/DemoSourceStorage",
                "assistant": "Ragna/DemoAssistant",
                "params": {},
            },
        )
        .raise_for_status()
        .json()
    )
    client.post(f"/chats/{chat['id']}/prepare").raise_for_status()
    for _ in range(3):
        client.post(
            f"/chats/{chat['id']}/answer",
            params={"prompt": "What is Ragna? Please, I need to know!"},
        ).raise_for_status()

    ## chat 3

    chat = (
        client.post(
            "/chats",
            json={
                "name": (
                    "Really long chat name that likely needs to be truncated somehow. "
                    "If you can read this, truncating failed :boom:"
                ),
                "documents": [documents[i] for i in [0, 2, 4]],
                "source_storage": "Ragna/DemoSourceStorage",
                "assistant": "Ragna/DemoAssistant",
                "params": {},
            },
        )
        .raise_for_status()
        .json()
    )
    client.post(f"/chats/{chat['id']}/prepare").raise_for_status()
    client.post(
        f"/chats/{chat['id']}/answer",
        params={"prompt": "Hello!"},
    ).raise_for_status()
    client.post(
        f"/chats/{chat['id']}/answer",
        params={"prompt": "Ok, in that case show me some pretty markdown!"},
    ).raise_for_status()

    chats = client.get("/chats").raise_for_status().json()
    print(json.dumps(chats))


if __name__ == "__main__":
    main()
