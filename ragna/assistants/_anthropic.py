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

    def _instructize_prompt(self, prompt: str, sources: list[Source]) -> str:
        # See https://docs.anthropic.com/claude/docs/introduction-to-prompt-design#human--assistant-formatting
        instruction = (
            "\n\nHuman: "
            "Use the following pieces of context to answer the question at the end. "
            "If you don't know the answer, just say so. Don't try to make up an answer.\n"
        )
        instruction += "\n\n".join(source.content for source in sources)
        return f"{instruction}\n\nQuestion: {prompt}\n\nAssistant:"

    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> AsyncIterator[str]:
        import httpx_sse

        # See https://docs.anthropic.com/claude/reference/streaming
        async with httpx_sse.aconnect_sse(
            self._client,
            "POST",
            "https://api.anthropic.com/v1/complete",
            headers={
                "accept": "application/json",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "x-api-key": self._api_key,
            },
            json={
                "model": self._MODEL,
                "prompt": self._instructize_prompt(prompt, sources),
                "max_tokens_to_sample": max_new_tokens,
                "temperature": 0.0,
                "stream": True,
            },
        ) as event_source:
            await self._assert_api_call_is_success(event_source.response)

            async for sse in event_source.aiter_sse():
                data = json.loads(sse.data)
                if data["type"] != "completion":
                    continue
                elif "error" in data:
                    raise RagnaException(data["error"].pop("message"), **data["error"])
                elif data["stop_reason"] is not None:
                    break

                yield cast(str, data["completion"])


class ClaudeInstant(AnthropicApiAssistant):
    """[Claude Instant](https://docs.anthropic.com/claude/reference/selecting-a-model)

    !!! info "Required environment variables"

        - `ANTHROPIC_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "claude-instant-1"


class Claude(AnthropicApiAssistant):
    """[Claude](https://docs.anthropic.com/claude/reference/selecting-a-model)

    !!! info "Required environment variables"

        - `ANTHROPIC_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "claude-2"
