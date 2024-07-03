import abc
from functools import cached_property
from typing import Any, AsyncIterator, Optional, cast

from ragna.core import Message, MessageRole

from ._http_api import HttpApiAssistant, HttpStreamingProtocol


class OpenaiLikeHttpApiAssistant(HttpApiAssistant):
    _MODEL: Optional[str]

    @property
    @abc.abstractmethod
    def _url(self) -> str: ...

    # TODO: move to user config
    def _make_system_content(self) -> str:
        # See https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
        instruction = (
            "You are a helpful assistant that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the included messages below to generate the answer."
        )

        return Message(
            content=instruction,
            role=MessageRole.SYSTEM,
        )

    def _format_message_sources(self, messages: list[Message]) -> str:
        sources_prompt = "Include the following sources in your answer:"
        formatted_messages = []
        for message in messages:
            if message.role == MessageRole.USER:
                formatted_messages.append(
                    {
                        "content": sources_prompt
                        + "\n\n".join(source.content for source in message.sources),
                        "role": MessageRole.SYSTEM,
                    }
                )

            formatted_messages.append(
                {"content": message.content, "role": message.role}
            )
        return formatted_messages

    def _stream(
        self,
        messages: list[dict],
        *,
        max_new_tokens: int,
    ) -> AsyncIterator[dict[str, Any]]:
        # See https://platform.openai.com/docs/api-reference/chat/create
        # and https://platform.openai.com/docs/api-reference/chat/streaming
        headers = {
            "Content-Type": "application/json",
        }
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"

        json_ = {
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": max_new_tokens,
            "stream": True,
        }
        if self._MODEL is not None:
            json_["model"] = self._MODEL

        return self._call_api("POST", self._url, headers=headers, json=json_)

    async def answer(
        self,
        messages: list[Message] = [],
        *,
        max_new_tokens: int = 256,
    ) -> AsyncIterator[str]:
        formatted_messages = self._format_message_sources(messages)
        async for data in self._stream(
            formatted_messages, max_new_tokens=max_new_tokens
        ):
            choice = data["choices"][0]
            if choice["finish_reason"] is not None:
                break

            yield cast(str, choice["delta"]["content"])


class OpenaiAssistant(OpenaiLikeHttpApiAssistant):
    _API_KEY_ENV_VAR = "OPENAI_API_KEY"
    _STREAMING_PROTOCOL = HttpStreamingProtocol.SSE

    @classmethod
    def display_name(cls) -> str:
        return f"OpenAI/{cls._MODEL}"

    @cached_property
    def _url(self) -> str:
        return "https://api.openai.com/v1/chat/completions"


class Gpt35Turbo16k(OpenaiAssistant):
    """[OpenAI GPT-3.5](https://platform.openai.com/docs/models/gpt-3-5)

    !!! info "Required environment variables"

        - `OPENAI_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "gpt-3.5-turbo-16k"


class Gpt4(OpenaiAssistant):
    """[OpenAI GPT-4](https://platform.openai.com/docs/models/gpt-4)

    !!! info "Required environment variables"

        - `OPENAI_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "gpt-4"
