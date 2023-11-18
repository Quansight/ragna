import asyncio
import inspect

import pytest

import ragna.core
from ragna import Rag
from ragna.assistants import RagnaDemoAssistant
from ragna.source_storages import RagnaDemoSourceStorage


async def e2e_async(*, documents, source_storage, assistant):
    async with Rag().chat(
        documents=documents,
        source_storage=source_storage,
        assistant=assistant,
    ) as chat:
        return await chat.aanswer("?")


async def e2e_sync_in_async(*, documents, source_storage, assistant):
    with Rag().chat(
        documents=documents,
        source_storage=source_storage,
        assistant=assistant,
    ) as chat:
        return chat("?")


def e2e_sync(*, documents, source_storage, assistant):
    with Rag().chat(
        documents=documents,
        source_storage=source_storage,
        assistant=assistant,
    ) as chat:
        return chat("?")


@pytest.mark.parametrize("e2e_fn", [e2e_async, e2e_sync_in_async, e2e_sync])
def test_e2e(tmp_local_root, e2e_fn):
    document_root = tmp_local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("!\n")

    document = ragna.core.LocalDocument.from_path(document_path)

    answer = e2e_fn(
        documents=[document],
        source_storage=RagnaDemoSourceStorage,
        assistant=RagnaDemoAssistant,
    )
    if inspect.iscoroutine(answer):
        answer = asyncio.run(answer)

    assert isinstance(answer, ragna.core.Message)
    assert answer.role is ragna.core.MessageRole.ASSISTANT
    assert {source.document.name for source in answer.sources} == {document.name}
