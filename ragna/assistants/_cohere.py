from ._api import ApiAssistant


class CohereApiAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "COHERE_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def display_name(cls) -> str:
        return f"Cohere/{cls._MODEL}"
