import asyncio

import pytest

from ragna import Rag
from ragna.assistants import RagnaDemoAssistant
from ragna.core import LocalDocument, Message, MessageRole, MetadataFilter
from ragna.source_storages import RagnaDemoSourceStorage


@pytest.mark.parametrize("input_type", ["corpus", "metadata_filter", "documents"])
def test_e2e(tmp_local_root, input_type):
    async def main(*, input, source_storage, assistant):
        async with Rag().chat(
            input=input,
            source_storage=source_storage,
            assistant=assistant,
        ) as chat:
            return await chat.answer("?")

    document_root = tmp_local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("!\n")

    document = LocalDocument.from_path(document_path)

    source_storage = RagnaDemoSourceStorage()
    if input_type == "documents":
        input = [document]
    else:
        source_storage.store("default", [document])

        if input_type == "corpus":
            input = None
        elif input_type == "metadata_filter":
            input = MetadataFilter.eq("document_id", str(document.id))

    answer = asyncio.run(
        main(
            input=input,
            source_storage=source_storage,
            assistant=RagnaDemoAssistant,
        )
    )

    assert isinstance(answer, Message)
    assert answer.role is MessageRole.ASSISTANT
    assert {source.document_name for source in answer.sources} == {document.name}
