import json
from typing import AsyncIterator, cast

import httpx_sse

from ragna.core import Source

from ._api import ApiAssistant


class OpenaiApiAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "OPENAI_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def display_name(cls) -> str:
        return f"OpenAI/{cls._MODEL}"

    @property
    def max_input_size(self) -> int:
        return self._CONTEXT_SIZE

    def _make_system_content(self, sources: list[Source]) -> str:
        # See https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
        instruction = (
            "You are an helpful assistants that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the sources below to generate the answer."
        )
        return instruction + "\n\n".join(source.content for source in sources)

    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> AsyncIterator[str]:
        # See https://platform.openai.com/docs/api-reference/chat/create
        # and https://platform.openai.com/docs/api-reference/chat/streaming
        async with httpx_sse.aconnect_sse(
            self._client,
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            json={
                "messages": [
                    {
                        "role": "system",
                        "content": self._make_system_content(sources),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "model": self._MODEL,
                "temperature": 0.0,
                "max_tokens": max_new_tokens,
                "stream": True,
            },
        ) as event_source:
            await self._assert_api_call_is_success(event_source.response)

            async for sse in event_source.aiter_sse():
                data = json.loads(sse.data)
                choice = data["choices"][0]
                if choice["finish_reason"] is not None:
                    break

                yield cast(str, choice["delta"]["content"])


class Gpt35Turbo16k(OpenaiApiAssistant):
    """[OpenAI GPT-3.5](https://platform.openai.com/docs/models/gpt-3-5)

    !!! info "Required environment variables"

        - `OPENAI_API_KEY`
    """

    _MODEL = "gpt-3.5-turbo-16k"
    _CONTEXT_SIZE = 16_384


class Gpt4(OpenaiApiAssistant):
    """[OpenAI GPT-4](https://platform.openai.com/docs/models/gpt-4)

    !!! info "Required environment variables"

        - `OPENAI_API_KEY`
    """

    _MODEL = "gpt-4"
    _CONTEXT_SIZE = 8_192
