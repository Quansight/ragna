import pytest
from fastapi import status

from ragna import assistants
from ragna.core import RagnaException
from ragna.deploy import Config
from tests.deploy.utils import make_api_app, make_api_client


@pytest.mark.parametrize("ignore_unavailable_components", [True, False])
def test_ignore_unavailable_components(ignore_unavailable_components):
    available_assistant = assistants.RagnaDemoAssistant
    assert available_assistant.is_available()

    unavailable_assistant = assistants.Gpt4
    assert not unavailable_assistant.is_available()

    config = Config(assistants=[available_assistant, unavailable_assistant])

    if ignore_unavailable_components:
        with make_api_client(
            config=config,
            ignore_unavailable_components=ignore_unavailable_components,
        ) as client:
            components = client.get("/api/components").raise_for_status().json()
            assert [assistant["title"] for assistant in components["assistants"]] == [
                available_assistant.display_name()
            ]
    else:
        with pytest.raises(RagnaException, match="not available"):
            make_api_app(
                config=config,
                ignore_unavailable_components=ignore_unavailable_components,
            )


def test_ignore_unavailable_components_at_least_one():
    unavailable_assistant = assistants.Gpt4
    assert not unavailable_assistant.is_available()

    config = Config(assistants=[unavailable_assistant])

    with pytest.raises(RagnaException, match="No component available"):
        make_api_app(
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

    with make_api_client(
        config=Config(), ignore_unavailable_components=False
    ) as client:
        document = (
            client.post("/api/documents", json=[{"name": document_path.name}])
            .raise_for_status()
            .json()[0]
        )

        with open(document_path, "rb") as file:
            client.put("/api/documents", files={"documents": (document["id"], file)})

        response = client.post(
            "/api/chats",
            json={
                "name": "test-chat",
                "input": [document["id"]],
                "source_storage": "unknown_source_storage",
                "assistant": "unknown_assistant",
                "corpus_name": "test-corpus",
                "params": {},
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        error = response.json()["error"]
        assert "Unknown component" in error["message"]
