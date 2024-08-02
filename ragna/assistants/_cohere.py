from typing import AsyncIterator, cast

from ragna.core import Message, RagnaException, Source

from ._http_api import HttpApiAssistant, HttpStreamingProtocol


class CohereAssistant(HttpApiAssistant):
    _API_KEY_ENV_VAR = "COHERE_API_KEY"
    _STREAMING_PROTOCOL = HttpStreamingProtocol.JSONL
    _MODEL: str

    @classmethod
    def display_name(cls) -> str:
        return f"Cohere/{cls._MODEL}"

    def _make_preamble(self) -> str:
        return (
            "You are a helpful assistant that answers user questions given the included context. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the included documents below to generate the answer."
        )

    def _make_source_documents(self, sources: list[Source]) -> list[dict[str, str]]:
        return [{"title": source.id, "snippet": source.content} for source in sources]

    async def answer(
        self, messages: list[Message], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        # See https://docs.cohere.com/docs/cochat-beta
        # See https://docs.cohere.com/reference/chat
        # See https://docs.cohere.com/docs/retrieval-augmented-generation-rag
        prompt, sources = (message := messages[-1]).content, message.sources
        async with self._call_api(
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
        ) as stream:
            async for event in stream:
                if event["event_type"] == "stream-end":
                    if event["event_type"] == "COMPLETE":
                        break

                    raise RagnaException(event["error_message"])
                if "text" in event:
                    yield cast(str, event["text"])


class Command(CohereAssistant):
    """
    [Cohere Command](https://docs.cohere.com/docs/models#command)

    !!! info "Required environment variables"

        - `COHERE_API_KEY`
    """

    _MODEL = "command"


class CommandLight(CohereAssistant):
    """
    [Cohere Command-Light](https://docs.cohere.com/docs/models#command)

    !!! info "Required environment variables"

        - `COHERE_API_KEY`
    """

    _MODEL = "command-light"
