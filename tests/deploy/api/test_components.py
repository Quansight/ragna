import pytest
from fastapi.testclient import TestClient

from ragna import assistants
from ragna.core import RagnaException
from ragna.deploy import Config
from ragna.deploy._api import app

from .utils import authenticate


@pytest.mark.parametrize("ignore_unavailable_components", [True, False])
def test_ignore_unavailable_components(ignore_unavailable_components):
    available_assistant = assistants.RagnaDemoAssistant
    assert available_assistant.is_available()

    unavailable_assistant = assistants.Gpt4
    assert not unavailable_assistant.is_available()

    config = Config(
        components=dict(assistants=[available_assistant, unavailable_assistant])
    )

    if ignore_unavailable_components:
        with TestClient(
            app(
                config=config,
                ignore_unavailable_components=ignore_unavailable_components,
            )
        ) as client:
            authenticate(client)

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

    config = Config(components=dict(assistants=[unavailable_assistant]))

    with pytest.raises(RagnaException, match="No component available"):
        app(
            config=config,
            ignore_unavailable_components=True,
        )
