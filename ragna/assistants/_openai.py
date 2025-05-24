import abc
from functools import cached_property
from typing import Any, AsyncContextManager, AsyncIterator, Optional, cast

from ragna.core import Message, Source

from ._http_api import HttpApiAssistant, HttpStreamingProtocol


class OpenaiLikeHttpApiAssistant(HttpApiAssistant):
    _MODEL: Optional[str]

    @property
    @abc.abstractmethod
    def _url(self) -> str: ...

    def _make_system_content(self, sources: list[Source]) -> str:
        # See https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
        instruction = (
            "You are an helpful assistants that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the sources below to generate the answer."
        )
        return instruction + "\n\n".join(source.content for source in sources)

    def _call_openai_api(
        self, messages: list[Message], *, max_new_tokens: int
    ) -> AsyncContextManager[AsyncIterator[dict[str, Any]]]:
        # See https://platform.openai.com/docs/api-reference/chat/create
        # and https://platform.openai.com/docs/api-reference/chat/streaming
        headers = {
            "Content-Type": "application/json",
        }
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"
        current_prompt = next(m for m in reversed(messages) if m.role == "user")
        json_ = {
            "messages": [
                {
                    "role": "system",
                    "content": self._make_system_content(current_prompt.sources),
                },
                *(
                    {
                        "role": message.role,
                        "content": message.content,
                    }
                    for message in messages
                    if message.role != "system"
                ),
            ],
            "temperature": 0.0,
            "max_tokens": max_new_tokens,
            "stream": True,
        }
        if self._MODEL is not None:
            json_["model"] = self._MODEL

        return self._call_api("POST", self._url, headers=headers, json=json_)

    async def answer(
        self, messages: list[Message], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        async with self._call_openai_api(
            messages, max_new_tokens=max_new_tokens
        ) as stream:
            async for data in stream:
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

    @classmethod
    def avatar(cls) -> str:
        """Return the avatar for this assistant in a chat."""
        return (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/"
            "ChatGPT_logo.svg/1024px-ChatGPT_logo.svg.png?20230318122128"
        )


class Gpt4(OpenaiAssistant):
    """[OpenAI GPT-4](https://platform.openai.com/docs/models/gpt-4)

    !!! info "Required environment variables"

        - `OPENAI_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "gpt-4"

    @classmethod
    def avatar(cls) -> str:
        """Return the avatar for this assistant in a chat."""
        return "https://upload.wikimedia.org/wikipedia/commons/a/a4/GPT-4.png"
