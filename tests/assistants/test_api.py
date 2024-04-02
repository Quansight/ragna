import os

import pytest

from ragna import assistants
from ragna._compat import anext
from ragna.assistants._api import (
    AuthenticatedApiAssistant,
    UnauthenticatedApiAssistant,
    _ApiAssistant,
)
from ragna.core import RagnaException
from tests.utils import skip_on_windows

API_ASSISTANTS = [
    assistant
    for assistant in assistants.__dict__.values()
    if isinstance(assistant, type)
    and issubclass(assistant, _ApiAssistant)
    and assistant is not _ApiAssistant
    and assistant is not AuthenticatedApiAssistant
    and assistant is not UnauthenticatedApiAssistant
]


@skip_on_windows
@pytest.mark.parametrize("assistant", API_ASSISTANTS)
async def test_api_call_error_smoke(mocker, assistant):
    mocker.patch.dict(os.environ, {assistant._API_KEY_ENV_VAR: "SENTINEL"})

    chunks = assistant().answer(prompt="?", sources=[])

    with pytest.raises(RagnaException, match="API call failed"):
        await anext(chunks)
