import sys

from ragna.core import Assistant, Source


class RagnaDemoAssistant(Assistant):
    @classmethod
    def display_name(cls):
        return "Ragna/DemoLLM"

    @property
    def context_size(self) -> int:
        return sys.maxsize

    def answer(self, prompt: str, sources: list[Source]) -> str:
        return (
            "I'm just pretending to be an LLM, "
            "so I can't actually help with your prompt."
        )
