import pydantic
import pytest

from ragna import Rag, assistants, source_storages
from ragna.core import LocalDocument


@pytest.fixture()
def demo_document(tmp_path, request):
    path = tmp_path / "demo_document.txt"
    with open(path, "w") as file:
        file.write(f"{request.node.name}\n")
    return LocalDocument.from_path(path)


class TestChat:
    def chat(self, documents, **params):
        return Rag().chat(
            documents=documents,
            source_storage=source_storages.RagnaDemoSourceStorage,
            assistant=assistants.RagnaDemoAssistant,
            **params,
        )

    def test_extra_params(self, demo_document):
        with pytest.raises(pydantic.ValidationError, match="not_supported_parameter"):
            self.chat(
                documents=[demo_document], not_supported_parameter="arbitrary_value"
            )

    def test_document_path(self, demo_document):
        chat = self.chat(documents=[demo_document.path])

        assert len(chat.documents) == 1
        document = chat.documents[0]

        assert isinstance(document, LocalDocument)
        assert document.path == demo_document.path
        assert document.name == demo_document.name
