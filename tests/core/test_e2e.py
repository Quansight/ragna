import asyncio

import ragna.core
from ragna import Rag
from ragna.assistants import RagnaDemoAssistant
from ragna.source_storages import RagnaDemoSourceStorage


def test_e2e(tmp_local_root):
    document_root = tmp_local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("!\n")
    document = ragna.core.LocalDocument.from_path(document_path)

    async def main():
        async with Rag().chat(
            documents=[document],
            source_storage=RagnaDemoSourceStorage,
            assistant=RagnaDemoAssistant,
        ) as chat:
            return await chat.aanswer("?")

    answer = asyncio.run(main())

    assert isinstance(answer, ragna.core.Message)
    assert answer.role is ragna.core.MessageRole.ASSISTANT
    assert {source.document.name for source in answer.sources} == {document.name}
