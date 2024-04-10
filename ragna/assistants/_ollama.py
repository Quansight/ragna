import contextlib
import json
import os
from typing import AsyncIterator, cast

import httpx
from httpx import Response

import ragna
from ragna.core import Assistant, RagnaException, Source


class OllamaApiAssistant(Assistant):
    _MODEL: str

    @classmethod
    def display_name(cls) -> str:
        return f"Ollama/{cls._MODEL}"

    def __init__(self, url: str = "http://localhost:11434/api/chat") -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=60,
        )
        self._url = os.environ.get("RAGNA_ASSISTANTS_OLLAMA_URL", url)

    @classmethod
    def is_available(cls) -> bool:
        if not super().is_available():
            return False

        try:
            return httpx.get("http://localhost:11434/").raise_for_status().is_success
        except httpx.HTTPError:
            return False

    def _make_system_content(self, sources: list[Source]) -> str:
        instruction = (
            "You are a helpful assistant that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the following sources to generate the answer."
        )
        return instruction + "\n\n".join(source.content for source in sources)

    async def _assert_api_call_is_success(self, response: Response) -> None:
        if response.is_success:
            return

        content = await response.aread()
        with contextlib.suppress(Exception):
            content = json.loads(content)

        raise RagnaException(
            "API call failed",
            request_method=response.request.method,
            request_url=str(response.request.url),
            response_status_code=response.status_code,
            response_content=content,
        )

    async def answer(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        async with self._client.stream(
            "POST",
            self._url,
            headers={
                "Content-Type": "application/json",
            },
            json={
                "messages": [
                    {
                        "role": "system",
                        "content": self._make_system_content(sources),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "model": self._MODEL,
                "stream": True,
                "temperature": 0.0,
            },
        ) as response:
            await self._assert_api_call_is_success(response)

            async for chunk in response.aiter_lines():
                # This part modeled after https://github.com/ollama/ollama/blob/06a1508bfe456e82ba053ea554264e140c5057b5/examples/python-loganalysis/readme.md?plain=1#L57-L62
                if chunk:
                    json_data = json.loads(chunk)

                    if "error" in json_data:
                        raise RagnaException(json_data["error"])
                    if not json_data["done"]:
                        yield cast(str, json_data["message"]["content"])


class OllamaGemma2B(OllamaApiAssistant):
    """[Gemma:2B](https://ollama.com/library/gemma)"""

    _MODEL = "gemma:2b"


class OllamaPhi2(OllamaApiAssistant):
    """[Phi-2](https://ollama.com/library/phi)"""

    _MODEL = "phi"
