import contextlib
import json
import os
from typing import Any, AsyncIterator, Optional

import httpx
from httpx import Response

import ragna
from ragna.core import Assistant, EnvVarRequirement, RagnaException, Requirement


class HttpApiAssistant(Assistant):
    _API_KEY_ENV_VAR: Optional[str] = None

    @classmethod
    def requirements(cls) -> list[Requirement]:
        requirements: list[Requirement] = (
            [EnvVarRequirement(cls._API_KEY_ENV_VAR)]
            if cls._API_KEY_ENV_VAR is not None
            else []
        )
        requirements.extend(cls._extra_requirements())
        return requirements

    @classmethod
    def _extra_requirements(cls) -> list[Requirement]:
        return []

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=60,
        )
        self._api_key: Optional[str] = (
            os.environ[self._API_KEY_ENV_VAR]
            if self._API_KEY_ENV_VAR is not None
            else None
        )

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

    async def _stream_sse(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        import httpx_sse

        async with httpx_sse.aconnect_sse(
            self._client, method, url, **kwargs
        ) as event_source:
            await self._assert_api_call_is_success(event_source.response)

            async for sse in event_source.aiter_sse():
                yield json.loads(sse.data)

    async def _stream_jsonl(
        self, method: str, url: str, **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        async with self._client.stream(method, url, **kwargs) as response:
            await self._assert_api_call_is_success(response)

            async for chunk in response.aiter_lines():
                yield json.loads(chunk)
