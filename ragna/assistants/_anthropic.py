import json
from typing import AsyncIterator, cast

from ragna.core import PackageRequirement, RagnaException, Requirement, Source

from ._api import ApiAssistant


class AnthropicApiAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
    _MODEL: str

    @classmethod
    def _extra_requirements(cls) -> list[Requirement]:
        return [PackageRequirement("httpx_sse")]

    @classmethod
    def display_name(cls) -> str:
        return f"Anthropic/{cls._MODEL}"

    def _instructize_system_prompt(self, sources: list[Source]) -> str:
        # See https://docs.anthropic.com/claude/docs/system-prompts
        instruction = (
            "Use the following documents to answer the prompt. "
            "If you don't know the answer, just say so. Don't try to make up an answer."
            "Only use the included documents below to generate the answer.\n"
        )
        instruction += "\n\n".join(source.content for source in sources)
        return instruction

    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> AsyncIterator[str]:
        import httpx_sse

        # See https://docs.anthropic.com/claude/reference/messages_post
        # See https://docs.anthropic.com/claude/reference/streaming
        async with httpx_sse.aconnect_sse(
            self._client,
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers={
                "accept": "application/json",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "x-api-key": self._api_key,
            },
            json={
                "model": self._MODEL,
                "system": self._instructize_system_prompt(sources),
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "max_tokens": max_new_tokens,
                "temperature": 0.0,
                "stream": True,
            },
        ) as event_source:
            await self._assert_api_call_is_success(event_source.response)

            async for sse in event_source.aiter_sse():
                data = json.loads(sse.data)
                # See https://docs.anthropic.com/claude/reference/messages-streaming#raw-http-stream-response
                if data["type"] != "content_block_delta":
                    continue
                elif data["type"] == "error":
                    raise RagnaException(data["error"].pop("message"), **data["error"])
                elif data["type"] == "message_stop":
                    break
                # breakpoint()
                yield cast(str, data["delta"].pop("text"))


class Claude(AnthropicApiAssistant):
    """[Claude](https://docs.anthropic.com/claude/reference/selecting-a-model)

    !!! info "Required environment variables"

        - `ANTHROPIC_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "claude-3-opus-20240229"
