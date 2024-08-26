import json

import pytest

from ragna.deploy import Config
from tests.deploy.utils import (
    TestAssistant,
    make_api_client,
)
from tests.utils import skip_on_windows


@skip_on_windows
@pytest.mark.parametrize("multiple_answer_chunks", [True, False])
@pytest.mark.parametrize("stream_answer", [True, False])
def test_e2e(tmp_local_root, multiple_answer_chunks, stream_answer):
    config = Config(local_root=tmp_local_root, assistants=[TestAssistant])

    document_root = config.local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("!\n")

    with make_api_client(config=config, ignore_unavailable_components=False) as client:
        assert client.get("/api/chats").raise_for_status().json() == []

        documents = (
            client.post("/api/documents", json=[{"name": document_path.name}])
            .raise_for_status()
            .json()
        )
        assert len(documents) == 1
        document = documents[0]
        assert document["name"] == document_path.name

        with open(document_path, "rb") as file:
            client.put("/api/documents", files={"documents": (document["id"], file)})

        components = client.get("/api/components").raise_for_status().json()
        supported_documents = components["documents"]
        assert set(supported_documents) == config.document.supported_suffixes()
        source_storages = [
            json_schema["title"] for json_schema in components["source_storages"]
        ]
        assert source_storages == [
            source_storage.display_name() for source_storage in config.source_storages
        ]
        assistants = [json_schema["title"] for json_schema in components["assistants"]]
        assert assistants == [
            assistant.display_name() for assistant in config.assistants
        ]

        source_storage = source_storages[0]
        assistant = assistants[0]

        chat_creation = {
            "name": "test-chat",
            "document_ids": [document["id"]],
            "source_storage": source_storage,
            "assistant": assistant,
            "params": {"multiple_answer_chunks": multiple_answer_chunks},
        }
        chat = client.post("/api/chats", json=chat_creation).raise_for_status().json()
        for field in ["name", "source_storage", "assistant", "params"]:
            assert chat[field] == chat_creation[field]
        assert [document["id"] for document in chat["documents"]] == chat_creation[
            "document_ids"
        ]
        assert not chat["prepared"]
        assert chat["messages"] == []

        assert client.get("/api/chats").raise_for_status().json() == [chat]
        assert client.get(f"/api/chats/{chat['id']}").raise_for_status().json() == chat

        message = (
            client.post(f"/api/chats/{chat['id']}/prepare").raise_for_status().json()
        )
        assert message["role"] == "system"
        assert message["sources"] == []

        chat = client.get(f"/api/chats/{chat['id']}").raise_for_status().json()
        assert chat["prepared"]
        assert len(chat["messages"]) == 1
        assert chat["messages"][-1] == message

        prompt = "?"
        if stream_answer:
            with client.stream(
                "POST",
                f"/api/chats/{chat['id']}/answer",
                json={"prompt": prompt, "stream": True},
            ) as response:
                chunks = [json.loads(chunk) for chunk in response.iter_lines()]
            message = chunks[0]
            assert all(chunk["sources"] is None for chunk in chunks[1:])
            message["content"] = "".join(chunk["content"] for chunk in chunks)
        else:
            message = (
                client.post(f"/api/chats/{chat['id']}/answer", json={"prompt": prompt})
                .raise_for_status()
                .json()
            )

        assert message["role"] == "assistant"
        assert {source["document"]["name"] for source in message["sources"]} == {
            document_path.name
        }

        chat = client.get(f"/api/chats/{chat['id']}").raise_for_status().json()
        assert len(chat["messages"]) == 3
        assert chat["messages"][-1] == message
        assert (
            chat["messages"][-2]["role"] == "user"
            and chat["messages"][-2]["sources"] == message["sources"]
            and chat["messages"][-2]["content"] == prompt
        )

        client.delete(f"/api/chats/{chat['id']}").raise_for_status()
        assert client.get("/api/chats").raise_for_status().json() == []
