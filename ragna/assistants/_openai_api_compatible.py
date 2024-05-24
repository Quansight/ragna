import json
import os
from typing import AsyncIterator, cast

import httpx

import ragna
from ragna.core import PackageRequirement, Requirement, Source

from ._api import ApiAssistant


class OpenAIApiCompatible(ApiAssistant):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=60,
        )
        self._base_url = os.environ.get("BASE_URL")

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("httpx_sse")]

    @classmethod
    def display_name(cls) -> str:
        return "OpenAIApiCompatible"

    def _make_system_content(self, sources: list[Source]) -> str:
        instruction = (
            "You are an helpful assistants that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the sources below to generate the answer."
        )
        return instruction + "\n\n".join(source.content for source in sources)

    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> AsyncIterator[str]:
        import httpx_sse

        async with httpx_sse.aconnect_sse(
            self._client,
            "POST",
            f"{self._base_url}/v1/chat/completions",
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
                "temperature": 0.0,
                "max_tokens": max_new_tokens,
                "stream": True,
            },
        ) as event_source:
            await self._assert_api_call_is_success(event_source.response)
            async for sse in event_source.aiter_sse():
                data = json.loads(sse.data)
                choice = data["choices"][0]
                if choice["finish_reason"] is not None:
                    break
                try:
                    yield cast(str, choice["delta"]["content"])
                except KeyError:
                    pass
