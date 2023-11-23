import asyncio

from ragna import Rag
from ragna.assistants import RagnaDemoAssistant
from ragna.core import LocalDocument, Message, MessageRole
from ragna.source_storages import RagnaDemoSourceStorage


def test_e2e(tmp_local_root):
    document_root = tmp_local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("!\n")

    document = LocalDocument.from_path(document_path)

    async def main(*, documents, source_storage, assistant):
        async with Rag().chat(
            documents=documents,
            source_storage=source_storage,
            assistant=assistant,
        ) as chat:
            return await chat.answer("?")

    answer = asyncio.run(
        main(
            documents=[document],
            source_storage=RagnaDemoSourceStorage,
            assistant=RagnaDemoAssistant,
        )
    )

    assert isinstance(answer, Message)
    assert answer.role is MessageRole.ASSISTANT
    assert {source.document.name for source in answer.sources} == {document.name}
