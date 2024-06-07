import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ragna import assistants
from ragna.core import RagnaException
from ragna.deploy import Config
from ragna.deploy._api import app
from tests.deploy.utils import authenticate_with_api


@pytest.mark.parametrize("ignore_unavailable_components", [True, False])
def test_ignore_unavailable_components(ignore_unavailable_components):
    available_assistant = assistants.RagnaDemoAssistant
    assert available_assistant.is_available()

    unavailable_assistant = assistants.Gpt4
    assert not unavailable_assistant.is_available()

    config = Config(assistants=[available_assistant, unavailable_assistant])

    if ignore_unavailable_components:
        with TestClient(
            app(
                config=config,
                ignore_unavailable_components=ignore_unavailable_components,
            )
        ) as client:
            authenticate_with_api(client)

            components = client.get("/components").raise_for_status().json()
            assert [assistant["title"] for assistant in components["assistants"]] == [
                available_assistant.display_name()
            ]
    else:
        with pytest.raises(RagnaException, match="not available"):
            app(
                config=config,
                ignore_unavailable_components=ignore_unavailable_components,
            )


def test_ignore_unavailable_components_at_least_one():
    unavailable_assistant = assistants.Gpt4
    assert not unavailable_assistant.is_available()

    config = Config(assistants=[unavailable_assistant])

    with pytest.raises(RagnaException, match="No component available"):
        app(
            config=config,
            ignore_unavailable_components=True,
        )


def test_unknown_component(tmp_local_root):
    config = Config(local_root=tmp_local_root)

    document_root = config.local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("!\n")

    with TestClient(
        app(config=Config(), ignore_unavailable_components=False)
    ) as client:
        authenticate_with_api(client)

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

        response = client.post(
            "/chats",
            json={
                "name": "test-chat",
                "source_storage": "unknown_source_storage",
                "assistant": "unknown_assistant",
                "params": {},
                "documents": [document],
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        error = response.json()["error"]
        assert "Unknown component" in error["message"]
