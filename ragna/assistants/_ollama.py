import os
from functools import cached_property
from typing import AsyncIterator, cast

from ragna.core import Message, RagnaException

from ._http_api import HttpStreamingProtocol
from ._openai import OpenaiLikeHttpApiAssistant


class OllamaAssistant(OpenaiLikeHttpApiAssistant):
    """[Ollama](https://ollama.com/)

    To use this assistant, start the Ollama server manually. By default, the server
    is expected at `http://localhost:11434`. This can be changed with the
    `RAGNA_OLLAMA_BASE_URL` environment variable.
    """

    _API_KEY_ENV_VAR = None
    _STREAMING_PROTOCOL = HttpStreamingProtocol.JSONL
    _MODEL: str

    @classmethod
    def display_name(cls) -> str:
        return f"Ollama/{cls._MODEL}"

    @cached_property
    def _url(self) -> str:
        base_url = os.environ.get("RAGNA_OLLAMA_BASE_URL", "http://localhost:11434")
        return f"{base_url}/api/chat"

    async def answer(
        self, messages: list[Message], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        prompt, sources = (message := messages[-1]).content, message.sources
        async with self._call_openai_api(
            prompt, sources, max_new_tokens=max_new_tokens
        ) as stream:
            async for data in stream:
                # Modeled after
                # https://github.com/ollama/ollama/blob/06a1508bfe456e82ba053ea554264e140c5057b5/examples/python-loganalysis/readme.md?plain=1#L57-L62
                if "error" in data:
                    raise RagnaException(data["error"])
                if not data["done"]:
                    yield cast(str, data["message"]["content"])


class OllamaGemma2B(OllamaAssistant):
    """[Gemma:2B](https://ollama.com/library/gemma)"""

    _MODEL = "gemma:2b"


class OllamaLlama2(OllamaAssistant):
    """[Llama 2](https://ollama.com/library/llama2)"""

    _MODEL = "llama2"


class OllamaLlava(OllamaAssistant):
    """[Llava](https://ollama.com/library/llava)"""

    _MODEL = "llava"


class OllamaMistral(OllamaAssistant):
    """[Mistral](https://ollama.com/library/mistral)"""

    _MODEL = "mistral"


class OllamaMixtral(OllamaAssistant):
    """[Mixtral](https://ollama.com/library/mixtral)"""

    _MODEL = "mixtral"


class OllamaOrcaMini(OllamaAssistant):
    """[Orca Mini](https://ollama.com/library/orca-mini)"""

    _MODEL = "orca-mini"


class OllamaPhi2(OllamaAssistant):
    """[Phi-2](https://ollama.com/library/phi)"""

    _MODEL = "phi"
