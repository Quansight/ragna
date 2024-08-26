import json

import httpx
import pytest
from fastapi.testclient import TestClient

from ragna.deploy import Config
from ragna.deploy._api import app
from tests.deploy.utils import TestAssistant, authenticate_with_api
from tests.utils import skip_on_windows


@skip_on_windows
@pytest.mark.parametrize("multiple_answer_chunks", [True, False])
@pytest.mark.parametrize("stream_answer", [True, False])
@pytest.mark.parametrize("corpus_name", ["default", "test-corpus"])
def test_e2e(tmp_local_root, multiple_answer_chunks, stream_answer, corpus_name):
    config = Config(local_root=tmp_local_root, assistants=[TestAssistant])

    document_root = config.local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("!\n")

    with TestClient(app(config=config, ignore_unavailable_components=False)) as client:
        authenticate_with_api(client)

        assert client.get("/chats").raise_for_status().json() == []

        document_upload = (
            client.post("/document", json={"name": document_path.name})
            .raise_for_status()
            .json()
        )
        document = document_upload["document"]
        assert document["name"] == document_path.name

        parameters = document_upload["parameters"]
        with open(document_path, "rb") as file:
            client.request(
                parameters["method"],
                parameters["url"],
                data=parameters["data"],
                files={"file": file},
            )

        components = client.get("/components").raise_for_status().json()
        documents = components["documents"]
        assert set(documents) == config.document.supported_suffixes()
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

        chat_metadata = {
            "name": "test-chat",
            "source_storage": source_storage,
            "assistant": assistant,
            "corpus_name": corpus_name,
            "params": {"multiple_answer_chunks": multiple_answer_chunks},
            "input": [document],
        }
        chat = client.post("/chats", json=chat_metadata).raise_for_status().json()
        assert chat["metadata"] == chat_metadata
        assert not chat["prepared"]
        assert chat["messages"] == []

        corpuses = client.get("/corpuses").raise_for_status().json()
        assert corpuses == {source_storage: []}

        corpuses_metadata = client.get("/corpuses/metadata").raise_for_status().json()
        assert corpuses_metadata == {source_storage: []}

        assert client.get("/chats").raise_for_status().json() == [chat]
        assert client.get(f"/chats/{chat['id']}").raise_for_status().json() == chat

        message = client.post(f"/chats/{chat['id']}/prepare").raise_for_status().json()
        assert message["role"] == "system"
        assert message["sources"] == []

        chat = client.get(f"/chats/{chat['id']}").raise_for_status().json()
        assert chat["prepared"]
        assert len(chat["messages"]) == 1
        assert chat["messages"][-1] == message

        corpuses = client.get("/corpuses").raise_for_status().json()
        assert corpuses == {source_storage: [corpus_name]}

        corpuses = (
            client.get("/corpuses", params={"source_storage": source_storage})
            .raise_for_status()
            .json()
        )
        assert corpuses == {source_storage: [corpus_name]}

        with pytest.raises(httpx.HTTPStatusError, match="422 Unprocessable Entity"):
            client.get(
                "/corpuses", params={"source_storage": "unknown_source_storage"}
            ).raise_for_status()

        corpuses = client.get("/corpuses/metadata").raise_for_status().json()
        # assert corpuses == {source_storage: {corpus_name: {}}}

        corpuses = (
            client.get(
                "/corpuses/metadata",
                params={"source_storage": source_storage, corpus_name: corpus_name},
            )
            .raise_for_status()
            .json()
        )
        # assert corpuses == {source_storage: {corpus_name: {}}}

        with pytest.raises(httpx.HTTPStatusError, match="422 Unprocessable Entity"):
            client.get(
                "/corpuses/metadata",
                params={"source_storage": "unknown_source_storage"},
            ).raise_for_status()

        prompt = "?"
        if stream_answer:
            with client.stream(
                "POST",
                f"/chats/{chat['id']}/answer",
                json={"prompt": prompt, "stream": True},
            ) as response:
                chunks = [json.loads(chunk) for chunk in response.iter_lines()]
            message = chunks[0]
            assert all(chunk["sources"] is None for chunk in chunks[1:])
            message["content"] = "".join(chunk["content"] for chunk in chunks)
        else:
            message = (
                client.post(f"/chats/{chat['id']}/answer", json={"prompt": prompt})
                .raise_for_status()
                .json()
            )

        assert message["role"] == "assistant"
        assert {source["document_name"] for source in message["sources"]} == {
            document_path.name
        }

        chat = client.get(f"/chats/{chat['id']}").raise_for_status().json()
        assert len(chat["messages"]) == 3
        assert chat["messages"][-1] == message
        assert (
            chat["messages"][-2]["role"] == "user"
            and chat["messages"][-2]["sources"] == message["sources"]
            and chat["messages"][-2]["content"] == prompt
        )

        client.delete(f"/chats/{chat['id']}").raise_for_status()
        assert client.get("/chats").raise_for_status().json() == []
