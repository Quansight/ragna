import os

import pytest

from ragna import assistants
from ragna._compat import anext
from ragna.assistants._http_api import HttpApiAssistant
from ragna.core import RagnaException
from tests.utils import skip_on_windows

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

    chunks = assistant().answer(prompt="?", sources=[])

    with pytest.raises(RagnaException, match="API call failed"):
        await anext(chunks)
