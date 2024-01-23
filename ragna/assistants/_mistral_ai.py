from ._openai import OpenaiApiAssistant


class Mixtral8x7B(OpenaiApiAssistant):
    @classmethod
    def display_name(cls) -> str:
        return "MistralAI/Mixtral-8x7B"

    _MODEL = "gpt-3.5-turbo-16k"
    _CONTEXT_SIZE = 16_384
