from ragna.extensions import hookimpl, Source

from ._llm_api import LlmApi


class AnthropicLlmApi(LlmApi):
    _API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def display_name(cls):
        return f"Anthropic/{cls._MODEL}"

    @property
    def context_size(self) -> int:
        return self._CONTEXT_SIZE

    def _instructize_prompt(self, prompt: str, sources: list[Source]) -> str:
        # See https://docs.anthropic.com/claude/docs/introduction-to-prompt-design#human--assistant-formatting
        instruction = (
            "\n\nHuman: "
            "Use the following pieces of context to answer the question at the end. "
            "If you don't know the answer, just say so. Don't try to make up an answer.\n"
        )
        instruction += "\n\n".join(source.text for source in sources)
        return f"{instruction}\n\nQuestion: {prompt}\n\nAssistant:"

    def _call_api(self, prompt: str, sources: list[Source], *, max_new_tokens):
        import requests

        # See https://docs.anthropic.com/claude/reference/complete_post
        response = requests.post(
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
        if not response.ok:
            self._failed_api_call(
                status_code=response.status_code, response=response.json()
            )
        return response.json()["completion"]


class AnthropicClaude1InstantLlm(AnthropicLlmApi):
    # https://docs.anthropic.com/claude/reference/selecting-a-model
    _MODEL = "claude-instant-1"
    _CONTEXT_SIZE = 100_000


@hookimpl(specname="ragna_llm")
def anthropic_claude_1_instant_llm():
    return AnthropicClaude1InstantLlm


class AnthropicClaude2(AnthropicLlmApi):
    # https://docs.anthropic.com/claude/reference/selecting-a-model
    _MODEL = "claude-2"
    _CONTEXT_SIZE = 100_000


@hookimpl(specname="ragna_llm")
def anthropic_claude_2_llm():
    return AnthropicClaude2
