from typing import Any, AsyncIterator, Union, cast

from ragna.core import Message, MessageRole, RagnaException, Source

from ._http_api import HttpApiAssistant, HttpStreamingProtocol


class CohereAssistant(HttpApiAssistant):
    _API_KEY_ENV_VAR = "COHERE_API_KEY"
    _STREAMING_PROTOCOL = HttpStreamingProtocol.JSONL
    _MODEL: str

    @classmethod
    def display_name(cls) -> str:
        return f"Cohere/{cls._MODEL}"

    def _make_rag_preamble(self) -> str:
        return (
            "You are a helpful assistant that answers user questions given the included context. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the included documents below to generate the answer."
        )

    def _make_rag_source_documents(self, sources: list[Source]) -> list[dict[str, str]]:
        return [{"title": source.id, "snippet": source.content} for source in sources]

    def _render_prompt(self, prompt: Union[str, list[Message]]) -> str:
        """
        Ingests ragna messages-list or a single string prompt and converts to assistant-appropriate format.

        Returns:
            prompt string
        """
        if isinstance(prompt, str):
            messages = [Message(content=prompt, role=MessageRole.USER)]
        else:
            messages = prompt

        for message in reversed(messages):
            if message.role is MessageRole.USER:
                return message.content
        else:
            raise RagnaException

    async def generate(
        self,
        prompt: Union[str, list[Message]],
        source_documents: list[dict[str, str]],
        *,
        system_prompt: str = "You are a helpful assistant.",
        max_new_tokens: int = 256,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Primary method for calling assistant inference, either as a one-off request from anywhere in ragna, or as part of self.answer()
        This method should be called for tasks like pre-processing, agentic tasks, or any other user-defined calls.

        Args:
            prompt: Either a single prompt string or a list of ragna messages
            system_prompt: System prompt string
            source_documents: List of source content dicts with 'title' and 'snippet' keys
            max_new_tokens: Max number of completion tokens (default 256)

        Returns:
            async streamed inference response string chunks
        """
        # See https://docs.cohere.com/docs/cochat-beta
        # See https://docs.cohere.com/reference/chat
        # See https://docs.cohere.com/docs/retrieval-augmented-generation-rag

        async with self._call_api(
            "POST",
            "https://api.cohere.ai/v1/chat",
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": f"Bearer {self._api_key}",
            },
            json={
                "preamble_override": system_prompt,
                "message": self._render_prompt(prompt),
                "model": self._MODEL,
                "stream": True,
                "temperature": 0.0,
                "max_tokens": max_new_tokens,
                "documents": source_documents,
            },
        ) as stream:
            async for data in stream:
                yield data

    async def answer(
        self, messages: list[Message], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        message = messages[-1]
        async for data in self.generate(
            prompt=message.content,
            system_prompt=self._make_rag_preamble(),
            source_documents=self._make_rag_source_documents(message.sources),
            max_new_tokens=max_new_tokens,
        ):
            if data["event_type"] == "stream-end":
                if data["event_type"] == "COMPLETE":
                    break

                raise RagnaException(data["error_message"])
            if "text" in data:
                yield cast(str, data["text"])


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
