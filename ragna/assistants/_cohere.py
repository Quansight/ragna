import json
from typing import AsyncIterator, cast

from ragna.core import RagnaException, Source

from ._api import ApiAssistant


class CohereApiAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "COHERE_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int = 4_000
    # See https://docs.cohere.com/docs/models#command

    @classmethod
    def display_name(cls) -> str:
        return f"Cohere/{cls._MODEL}"

    @property
    def max_input_size(self) -> int:
        return self._CONTEXT_SIZE

    def _make_preamble(self) -> str:
        return (
            "You are a helpful assistant that answers user questions given the included context. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the included documents below to generate the answer."
        )

    def _make_source_documents(self, sources: list[Source]) -> list[dict[str, str]]:
        return [{"title": source.id, "snippet": source.content} for source in sources]

    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> AsyncIterator[str]:
        # See https://docs.cohere.com/docs/cochat-beta
        # See https://docs.cohere.com/reference/chat
        # See https://docs.cohere.com/docs/retrieval-augmented-generation-rag
        async with self._client.stream(
            "POST",
            "https://api.cohere.ai/v1/chat",
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": f"Bearer {self._api_key}",
            },
            json={
                "preamble_override": self._make_preamble(),
                "message": prompt,
                "model": self._MODEL,
                "stream": True,
                "temperature": 0.0,
                "max_tokens": max_new_tokens,
                "documents": self._make_source_documents(sources),
            },
        ) as response:
            await self._assert_api_call_is_success(response)

            async for chunk in response.aiter_lines():
                event = json.loads(chunk)
                if event["event_type"] == "stream-end":
                    if event["event_type"] == "COMPLETE":
                        break

                    raise RagnaException(event["error_message"])
                if "text" in event:
                    yield cast(str, event["text"])


class Command(CohereApiAssistant):
    """
    [Cohere Command](https://docs.cohere.com/docs/models#command)

    !!! info "Required environment variables"

        - `COHERE_API_KEY`
    """

    _MODEL = "command"


class CommandLight(CohereApiAssistant):
    """
    [Cohere Command-Light](https://docs.cohere.com/docs/models#command)

    !!! info "Required environment variables"

        - `COHERE_API_KEY`
    """

    _MODEL = "command-light"
