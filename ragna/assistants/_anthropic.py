from typing import cast

from ragna.core import RagnaException, Source

from ._api import ApiAssistant


class AnthropicApiAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def display_name(cls) -> str:
        return f"Anthropic/{cls._MODEL}"

    @property
    def max_input_size(self) -> int:
        return self._CONTEXT_SIZE

    def _instructize_prompt(self, prompt: str, sources: list[Source]) -> str:
        # See https://docs.anthropic.com/claude/docs/introduction-to-prompt-design#human--assistant-formatting
        instruction = (
            "\n\nHuman: "
            "Use the following pieces of context to answer the question at the end. "
            "If you don't know the answer, just say so. Don't try to make up an answer.\n"
        )
        instruction += "\n\n".join(source.content for source in sources)
        return f"{instruction}\n\nQuestion: {prompt}\n\nAssistant:"

    def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> str:
        # # See https://docs.anthropic.com/claude/reference/complete_post
        response = self._client.post(
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
            },
        )
        if response.is_error:
            raise RagnaException(
                status_code=response.status_code, response=response.json()
            )
        return cast(str, response.json()["completion"])


class ClaudeInstant(AnthropicApiAssistant):
    """[Claude Instant](https://docs.anthropic.com/claude/reference/selecting-a-model)

    !!! info "Required environment variables"

        - `ANTHROPIC_API_KEY`
    """

    _MODEL = "claude-instant-1"
    _CONTEXT_SIZE = 100_000


class Claude(AnthropicApiAssistant):
    """[Claude](https://docs.anthropic.com/claude/reference/selecting-a-model)

    !!! info "Required environment variables"

        - `ANTHROPIC_API_KEY`
    """

    _MODEL = "claude-2"
    _CONTEXT_SIZE = 100_000
