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

    def _call_api(self, prompt: str, sources: list[Source], *, chat_config):
        return f"I'm pretending to be {self._MODEL} from Anthropic"


class AnthropicClaude1InstantLlm(AnthropicLlmApi):
    # https://docs.anthropic.com/claude/reference/selecting-a-model
    _MODEL = "claude-1-instant"
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
