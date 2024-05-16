import io
import json

import pytest
from fastapi.testclient import TestClient

from ragna.core import Assistant, SourceStorage
from ragna.deploy import Config
from ragna.deploy._api import app

from .utils import authenticate


class FakeAssistant(Assistant):
    def answer(self, prompt, sources):
        if prompt == "Assistant Error":
            raise Exception("Assistant Error")


class FakeSourceStorage(SourceStorage):
    async def store(self, documents):
        pass

    async def retrieve(self, documents, prompt):
        if prompt == "SourceStorage Error":
            raise Exception("SourceStorage Error")


@pytest.mark.parametrize("prompt", ["Assistant Error", "SourceStorage Error"])
def test_internal_server_error_response(tmp_local_root, prompt):
    config = Config(
        local_root=tmp_local_root,
        assistants=[FakeAssistant],
        source_storages=[FakeSourceStorage],
    )

    with TestClient(app(config=config, ignore_unavailable_components=False)) as client:
        authenticate(client)

        document_upload = (
            client.post("/document", json={"name": "fake.txt"})
            .raise_for_status()
            .json()
        )
        document = document_upload["document"]
        parameters = document_upload["parameters"]
        client.request(
            parameters["method"],
            parameters["url"],
            data=parameters["data"],
            files={"file": io.BytesIO(b"!")},
        )

        chat_metadata = {
            "name": "test-chat",
            "source_storage": "FakeSourceStorage",
            "assistant": "FakeAssistant",
            "params": {},
            "documents": [document],
        }
        chat = client.post("/chats", json=chat_metadata).raise_for_status().json()

        _ = client.post(f"/chats/{chat['id']}/prepare").raise_for_status().json()

        with client.stream(
            "POST",
            f"/chats/{chat['id']}/answer",
            json={"prompt": prompt, "stream": True},
        ) as response:
            r = response.read()

        assert response.status_code == 500

        assert json.loads(r.decode("utf-8"))["detail"] == prompt
