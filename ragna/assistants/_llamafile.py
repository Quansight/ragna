import os

from ._openai import OpenaiCompliantHttpApiAssistant


class LlamafileAssistant(OpenaiCompliantHttpApiAssistant):
    _STREAMING_METHOD = "sse"
    _MODEL = None

    @property
    def _url(self) -> str:
        base_url = os.environ.get("RAGNA_LLAMAFILE_BASE_URL", "http://localhost:8080")
        return f"{base_url}/v1/chat/completions"
