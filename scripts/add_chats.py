import datetime
import json

import httpx


def main():
    client = httpx.Client()
    url = "http://127.0.0.1:31476"
    user = "Ragna"

    assert client.get(f"{url}").is_success

    ## documents

    documents = []
    for i in range(5):
        name = f"document{i}.txt"
        document_info = client.get(
            f"{url}/document", params={"user": user, "name": name}
        ).json()
        client.post(
            document_info["url"],
            data=document_info["data"],
            files={"file": f"Content of {name}".encode()},
        )
        documents.append(document_info["document"])

    ## chat 1

    chat = client.post(
        f"{url}/chats",
        params={"user": user},
        json={
            "name": "Test chat",
            "documents": documents[:2],
            "source_storage": "Ragna/DemoSourceStorage",
            "assistant": "Ragna/DemoAssistant",
            "params": {},
        },
    ).json()
    client.post(
        f"{url}/chats/{chat['id']}/prepare",
        params={"user": user},
    )
    client.post(
        f"{url}/chats/{chat['id']}/answer",
        params={"user": user, "prompt": "Hello!"},
    )

    ## chat 2

    chat = client.post(
        f"{url}/chats",
        params={"user": user},
        json={
            "name": f"Chat {datetime.datetime.now():%x %X}",
            "documents": documents[2:4],
            "source_storage": "Ragna/DemoSourceStorage",
            "assistant": "Ragna/DemoAssistant",
            "params": {},
        },
    ).json()
    client.post(
        f"{url}/chats/{chat['id']}/prepare",
        params={"user": user},
    )
    for _ in range(3):
        client.post(
            f"{url}/chats/{chat['id']}/answer",
            params={"user": user, "prompt": "What is Ragna? Please, I need to know!"},
        )

    ## chat 3

    chat = client.post(
        f"{url}/chats",
        params={"user": user},
        json={
            "name": "Really long chat name that likely needs to be truncated somehow. If you can read this, truncating failed :boom:",
            "documents": [documents[i] for i in [0, 2, 4]],
            "source_storage": "Ragna/DemoSourceStorage",
            "assistant": "Ragna/DemoAssistant",
            "params": {},
        },
    ).json()
    client.post(
        f"{url}/chats/{chat['id']}/prepare",
        params={"user": user},
    )
    client.post(
        f"{url}/chats/{chat['id']}/answer",
        params={"user": user, "prompt": "Hello!"},
    )
    client.post(
        f"{url}/chats/{chat['id']}/answer",
        params={
            "user": user,
            "prompt": "Ok, in that case show me some pretty markdown!",
        },
    )

    response = client.get(f"{url}/chats", params={"user": user})
    print(json.dumps(response.json()))


if __name__ == "__main__":
    main()
