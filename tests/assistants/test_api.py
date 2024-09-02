import asyncio
import itertools
import json
import os
import time
from pathlib import Path

import httpx
import pytest

from ragna import assistants
from ragna._utils import timeout_after
from ragna.assistants._http_api import HttpApiAssistant, HttpStreamingProtocol
from ragna.core import Message, RagnaException
from tests.utils import background_subprocess, get_available_port, skip_on_windows

HTTP_API_ASSISTANTS = [
    assistant
    for assistant in assistants.__dict__.values()
    if isinstance(assistant, type)
    and issubclass(assistant, HttpApiAssistant)
    and assistant is not HttpApiAssistant
]


@skip_on_windows
@pytest.mark.parametrize(
    "assistant",
    [assistant for assistant in HTTP_API_ASSISTANTS if assistant._API_KEY_ENV_VAR],
)
async def test_api_call_error_smoke(mocker, assistant):
    mocker.patch.dict(os.environ, {assistant._API_KEY_ENV_VAR: "SENTINEL"})

    messages = [Message(content="?", sources=[])]
    chunks = assistant().answer(messages)

    with pytest.raises(RagnaException, match="API call failed"):
        await anext(chunks)


@pytest.fixture
def streaming_server():
    port = get_available_port()
    base_url = f"http://localhost:{port}"

    with background_subprocess(
        "uvicorn",
        f"--app-dir={Path(__file__).parent}",
        f"--port={port}",
        "streaming_server:app",
    ):

        def up():
            try:
                return httpx.get(f"{base_url}/health").is_success
            except httpx.ConnectError:
                return False

        @timeout_after(10, message="Failed to start streaming server")
        def wait():
            while not up():
                time.sleep(0.2)

        wait()

        yield base_url


class HttpStreamingAssistant(HttpApiAssistant):
    _API_KEY_ENV_VAR = None

    @staticmethod
    def new(base_url, streaming_protocol):
        cls = type(
            f"{streaming_protocol.name.title()}{HttpStreamingAssistant.__name__}",
            (HttpStreamingAssistant,),
            dict(_STREAMING_PROTOCOL=streaming_protocol),
        )
        return cls(base_url)

    def __init__(self, base_url):
        super().__init__()
        self._endpoint = f"{base_url}/{self._STREAMING_PROTOCOL.name.lower()}"

    async def answer(self, messages):
        if self._STREAMING_PROTOCOL is HttpStreamingProtocol.JSON:
            parse_kwargs = dict(item="item")
        else:
            parse_kwargs = dict()

        async with self._call_api(
            "POST",
            self._endpoint,
            content=messages[-1].content,
            parse_kwargs=parse_kwargs,
        ) as stream:
            async for chunk in stream:
                if chunk.get("break"):
                    break

                yield chunk


@skip_on_windows
@pytest.mark.parametrize("streaming_protocol", list(HttpStreamingProtocol))
async def test_http_streaming(streaming_server, streaming_protocol):
    assistant = HttpStreamingAssistant.new(streaming_server, streaming_protocol)

    data = [{"chunk": chunk} for chunk in ["foo", "bar", "baz"]]
    expected_chunks = iter(data)
    actual_chunks = assistant.answer([Message(content=json.dumps(data))])
    async for actual_chunk in actual_chunks:
        expected_chunk = next(expected_chunks)
        assert actual_chunk == expected_chunk

    with pytest.raises(StopIteration):
        next(expected_chunks)


@skip_on_windows
@pytest.mark.parametrize("streaming_protocol", list(HttpStreamingProtocol))
def test_http_streaming_termination(streaming_server, streaming_protocol):
    # Non-regression test for https://github.com/Quansight/ragna/pull/462

    async def main():
        assistant = HttpStreamingAssistant.new(streaming_server, streaming_protocol)

        data = [
            {"chunk": "foo", "break": False},
            {"chunk": "bar", "break": False},
            {"chunk": "baz", "break": True},
        ]
        expected_chunks = itertools.takewhile(lambda chunk: not chunk["break"], data)
        actual_chunks = assistant.answer([Message(content=json.dumps(data))])
        async for actual_chunk in actual_chunks:
            expected_chunk = next(expected_chunks)
            assert actual_chunk == expected_chunk

        with pytest.raises(StopIteration):
            next(expected_chunks)

    asyncio.run(main())
