import contextlib
import enum
import json
import os
from typing import Any, AsyncIterator, Optional

import httpx

import ragna
from ragna._compat import anext
from ragna.core import (
    Assistant,
    EnvVarRequirement,
    PackageRequirement,
    RagnaException,
    Requirement,
)


async def assert_api_call_is_success(response: httpx.Response) -> None:
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


class HttpStreamingMethod(enum.Enum):
    SSE = enum.auto()
    JSONL = enum.auto()
    JSON = enum.auto()


class HttpStreamer:
    @classmethod
    def requirements(cls, method: HttpStreamingMethod) -> list[Requirement]:
        return {
            HttpStreamingMethod.SSE: [PackageRequirement("httpx_sse")],
            HttpStreamingMethod.JSON: [PackageRequirement("ijson")],
        }.get(method, [])

    def __init__(self, client: httpx.AsyncClient, method: HttpStreamingMethod) -> None:
        self._client = client
        self._method = method

    def __call__(
        self,
        method: str,
        url: str,
        *,
        streaming_kwargs: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        return {
            HttpStreamingMethod.SSE: self._sse,
            HttpStreamingMethod.JSONL: self._jsonl,
        }[self._method](method, url, streaming_kwargs=streaming_kwargs or {}, **kwargs)

    async def _sse(
        self,
        method: str,
        url: str,
        *,
        streaming_kwargs: dict[str, Any],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        import httpx_sse

        async with httpx_sse.aconnect_sse(
            self._client, method, url, **kwargs
        ) as event_source:
            await assert_api_call_is_success(event_source.response)

            async for sse in event_source.aiter_sse():
                yield json.loads(sse.data)

    async def _jsonl(
        self,
        method: str,
        url: str,
        *,
        streaming_kwargs: dict[str, Any],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        async with self._client.stream(method, url, **kwargs) as response:
            await assert_api_call_is_success(response)

            async for chunk in response.aiter_lines():
                yield json.loads(chunk)

    # ijson does not support reading from an (async) iterator, but only from file-like
    # objects, i.e. https://docs.python.org/3/tutorial/inputoutput.html#methods-of-file-objects.
    # See https://github.com/ICRAR/ijson/issues/44 for details.
    # ijson actually doesn't care about most of the file interface and only requires the
    # read() method to be present.
    class _AsyncIteratorReader:
        def __init__(self, ait: AsyncIterator[bytes]) -> None:
            self._ait = ait

        async def read(self, n: int) -> bytes:
            # n is usually used to indicate how many bytes to read, but since we want to
            # return a chunk as soon as it is available, we ignore the value of n. The
            # only exception is n == 0, which is used by ijson to probe the return type
            # and set up decoding.
            if n == 0:
                return b""
            return await anext(self._ait, b"")  # type: ignore[call-arg]

    async def _json(
        self,
        method: str,
        url: str,
        *,
        streaming_kwargs: dict[str, Any],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        import ijson

        item = streaming_kwargs["item"]
        chunk_size = streaming_kwargs.get("chunk_size", 16)

        async with self._client.stream(method, url, **kwargs) as response:
            await assert_api_call_is_success(response)

            async for chunk in ijson.items(
                self._AsyncIteratorReader(response.aiter_bytes(chunk_size)), item
            ):
                yield chunk


class HttpApiAssistant(Assistant):
    _API_KEY_ENV_VAR: Optional[str]
    _STREAMING_METHOD: Optional[HttpStreamingMethod]

    @classmethod
    def requirements(cls) -> list[Requirement]:
        requirements: list[Requirement] = (
            [EnvVarRequirement(cls._API_KEY_ENV_VAR)]
            if cls._API_KEY_ENV_VAR is not None
            else []
        )
        if cls._STREAMING_METHOD is not None:
            requirements.extend(HttpStreamer.requirements(cls._STREAMING_METHOD))
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
        self._stream = (
            HttpStreamer(self._client, self._STREAMING_METHOD)
            if self._STREAMING_METHOD is not None
            else None
        )
