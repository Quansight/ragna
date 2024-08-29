import contextlib
import enum
import json
import os
from typing import Any, AsyncContextManager, AsyncIterator, Optional

import httpx

import ragna
from ragna.core import (
    Assistant,
    EnvVarRequirement,
    PackageRequirement,
    RagnaException,
    Requirement,
)


class HttpStreamingProtocol(enum.Enum):
    SSE = enum.auto()
    JSONL = enum.auto()
    JSON = enum.auto()


class HttpApiCaller:
    @classmethod
    def requirements(cls, protocol: HttpStreamingProtocol) -> list[Requirement]:
        streaming_requirements: dict[HttpStreamingProtocol, list[Requirement]] = {
            HttpStreamingProtocol.SSE: [PackageRequirement("httpx_sse")],
            HttpStreamingProtocol.JSON: [PackageRequirement("ijson")],
        }
        return streaming_requirements.get(protocol, [])

    def __init__(
        self,
        client: httpx.AsyncClient,
        protocol: Optional[HttpStreamingProtocol] = None,
    ) -> None:
        self._client = client
        self._protocol = protocol

    def __call__(
        self,
        method: str,
        url: str,
        *,
        parse_kwargs: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> AsyncContextManager[AsyncIterator[Any]]:
        if self._protocol is None:
            call_method = self._no_stream
        else:
            call_method = {
                HttpStreamingProtocol.SSE: self._stream_sse,
                HttpStreamingProtocol.JSONL: self._stream_jsonl,
                HttpStreamingProtocol.JSON: self._stream_json,
            }[self._protocol]

        return call_method(method, url, parse_kwargs=parse_kwargs or {}, **kwargs)

    @contextlib.asynccontextmanager
    async def _no_stream(
        self,
        method: str,
        url: str,
        *,
        parse_kwargs: dict[str, Any],
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        response = await self._client.request(method, url, **kwargs)
        await self._assert_api_call_is_success(response)

        async def stream() -> AsyncIterator[Any]:
            yield response.json()

        yield stream()

    @contextlib.asynccontextmanager
    async def _stream_sse(
        self,
        method: str,
        url: str,
        *,
        parse_kwargs: dict[str, Any],
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        import httpx_sse

        async with httpx_sse.aconnect_sse(
            self._client, method, url, **kwargs
        ) as event_source:
            await self._assert_api_call_is_success(event_source.response)

            async def stream() -> AsyncIterator[Any]:
                async for sse in event_source.aiter_sse():
                    yield json.loads(sse.data)

            yield stream()

    @contextlib.asynccontextmanager
    async def _stream_jsonl(
        self,
        method: str,
        url: str,
        *,
        parse_kwargs: dict[str, Any],
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        async with self._client.stream(method, url, **kwargs) as response:
            await self._assert_api_call_is_success(response)

            async def stream() -> AsyncIterator[Any]:
                async for chunk in response.aiter_lines():
                    yield json.loads(chunk)

            yield stream()

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
            return await anext(self._ait, b"")

    @contextlib.asynccontextmanager
    async def _stream_json(
        self,
        method: str,
        url: str,
        *,
        parse_kwargs: dict[str, Any],
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        import ijson

        item = parse_kwargs["item"]
        chunk_size = parse_kwargs.get("chunk_size", 16)

        async with self._client.stream(method, url, **kwargs) as response:
            await self._assert_api_call_is_success(response)

            async def stream() -> AsyncIterator[Any]:
                async for chunk in ijson.items(
                    self._AsyncIteratorReader(response.aiter_bytes(chunk_size)), item
                ):
                    yield chunk

            yield stream()

    async def _assert_api_call_is_success(self, response: httpx.Response) -> None:
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


class HttpApiAssistant(Assistant):
    _API_KEY_ENV_VAR: Optional[str]
    _STREAMING_PROTOCOL: Optional[HttpStreamingProtocol]

    @classmethod
    def requirements(cls) -> list[Requirement]:
        requirements: list[Requirement] = (
            [EnvVarRequirement(cls._API_KEY_ENV_VAR)]
            if cls._API_KEY_ENV_VAR is not None
            else []
        )
        if cls._STREAMING_PROTOCOL is not None:
            requirements.extend(HttpApiCaller.requirements(cls._STREAMING_PROTOCOL))
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
        self._call_api = HttpApiCaller(self._client, self._STREAMING_PROTOCOL)
