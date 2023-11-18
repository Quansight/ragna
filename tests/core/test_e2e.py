import asyncio
import inspect

import pytest

from ragna import Rag
from ragna.assistants import RagnaDemoAssistant
from ragna.core import LocalDocument, Message, MessageRole
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


# FIXME: For whatever reason the timeout decorator is necessary. Without it,
#  e2e_sync_in_async is causing the tests to pass, but never terminate. I don't fully
#  understand why though. When killing the process manually, the error message indicates
#  that a thread is still running, although it shouldn't since the test has already
#  passed. This seems to only happen when running with pytest though and not during
#  normal operation. Weirdly enough, just putting the decorator here solves the issue.
#  Although we should still investigate what is actually happening.
@pytest.mark.parametrize("e2e_fn", [e2e_sync, e2e_async])
def test_e2e(tmp_local_root, e2e_fn):
    document_root = tmp_local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("!\n")

    document = LocalDocument.from_path(document_path)

    answer = e2e_fn(
        documents=[document],
        source_storage=RagnaDemoSourceStorage,
        assistant=RagnaDemoAssistant,
    )
    if inspect.iscoroutine(answer):
        answer = asyncio.run(answer)

    assert isinstance(answer, Message)
    assert answer.role is MessageRole.ASSISTANT
    assert {source.document.name for source in answer.sources} == {document.name}
