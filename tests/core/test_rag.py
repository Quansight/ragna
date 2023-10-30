import asyncio

import pydantic
import pytest

from ragna import Rag, assistants, source_storages


@pytest.fixture
def demo_document(tmp_path, request):
    path = tmp_path / "demo_document.txt"
    with open(path, "w") as file:
        file.write(f"{request.node.name}\n")
    return path


def test_chat_params_extra(demo_document):
    async def main():
        async with Rag().chat(
            documents=[demo_document],
            source_storage=source_storages.RagnaDemoSourceStorage,
            assistant=assistants.RagnaDemoAssistant,
            not_supported_parameter="arbitrary_value",
        ):
            pass

    with pytest.raises(pydantic.ValidationError, match="not_supported_parameter"):
        asyncio.run(main())
