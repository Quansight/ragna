import contextlib
import json
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

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=60,
        )

    def _make_system_content(self, sources: list[Source]) -> str:
        instruction = (
            "You are an helpful assistants that answers user questions given the context below. "
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

    async def _call_api(
        self,
        prompt: str,
        sources: list[Source],
        *,
        max_new_tokens: int,
        api_url: str = "http://localhost:11434/api/chat",
    ) -> AsyncIterator[str]:
        async with self._client.stream(
            "POST",
            api_url,
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

                    if not json_data["done"]:
                        yield cast(str, json_data["message"]["content"])
                else:
                    raise RagnaException("The response was empty.")

    async def answer(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        async for chunk in self._call_api(  # type: ignore[attr-defined, misc]
            prompt, sources, max_new_tokens=max_new_tokens
        ):
            yield chunk


class Gemma2B(OllamaApiAssistant):
    _MODEL = "gemma:2b"
