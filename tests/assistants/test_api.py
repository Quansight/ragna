import asyncio
import os

import pytest

from ragna import assistants
from ragna.core import RagnaException

API_ASSISTANTS = [
    assistant
    for assistant in assistants.__dict__.values()
    if isinstance(assistant, type)
    and issubclass(assistant, assistants._api.ApiAssistant)
    and assistant is not assistants._api.ApiAssistant
]


@pytest.mark.parametrize("assistant_cls", API_ASSISTANTS)
def test_api_call_error_smoke(mocker, assistant_cls):
    mocker.patch.dict(os.environ, {assistant_cls._API_KEY_ENV_VAR: "SENTINEL"})

    assistant = assistant_cls()

    async def run():
        return "".join(
            [chunk async for chunk in assistant.answer(prompt="?", sources=[])]
        )

    with pytest.raises(RagnaException, match="API call failed"):
        asyncio.run(run())
