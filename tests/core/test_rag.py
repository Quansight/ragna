import pytest

from ragna import Rag, assistants, source_storages
from ragna.core import Assistant, LocalDocument, RagnaException


@pytest.fixture()
def demo_document(tmp_path, request):
    path = tmp_path / "demo_document.txt"
    with open(path, "w") as file:
        file.write(f"{request.node.name}\n")
    return LocalDocument.from_path(path)


class TestChat:
    def chat(
        self,
        documents,
        source_storage=source_storages.RagnaDemoSourceStorage,
        assistant=assistants.RagnaDemoAssistant,
        **params,
    ):
        return Rag().chat(
            documents=documents,
            source_storage=source_storage,
            assistant=assistant,
            **params,
        )

    def test_params_validation_unknown(self, demo_document):
        params = {
            "bool_param": False,
            "int_param": 1,
            "float_param": 0.5,
            "string_param": "arbitrary_value",
        }
        with pytest.raises(RagnaException, match="unknown") as exc_info:
            self.chat(documents=[demo_document], **params)

        msg = str(exc_info.value)
        for param, value in params.items():
            assert f"{param}={value!r}" in msg

    def test_params_validation_missing(self, demo_document):
        class ValidationAssistant(Assistant):
            def answer(
                self,
                messages,
                bool_param: bool,
                int_param: int,
                float_param: float,
                string_param: str,
            ):
                pass

        with pytest.raises(RagnaException, match="missing") as exc_info:
            self.chat(documents=[demo_document], assistant=ValidationAssistant)

        msg = str(exc_info.value)
        for param, annotation in ValidationAssistant.answer.__annotations__.items():
            assert f"{param}: {annotation.__name__}" in msg

    def test_params_validation_wrong_type(self, demo_document):
        class ValidationAssistant(Assistant):
            def answer(
                self,
                messages,
                bool_param: bool,
                int_param: int,
                float_param: float,
                string_param: str,
            ):
                pass

        params = {
            "bool_param": 1,
            "int_param": 0.5,
            "float_param": "arbitrary_value",
            "string_param": False,
        }

        with pytest.raises(RagnaException, match="wrong type") as exc_info:
            self.chat(
                documents=[demo_document], assistant=ValidationAssistant, **params
            )

        msg = str(exc_info.value)
        for param, value in params.items():
            annotation = ValidationAssistant.answer.__annotations__[param]
            assert f"{param}: {annotation.__name__} = {value!r}" in msg

    def test_document_path(self, demo_document):
        chat = self.chat(documents=[demo_document.path])

        assert len(chat.documents) == 1
        document = chat.documents[0]

        assert isinstance(document, LocalDocument)
        assert document.path == demo_document.path
        assert document.name == demo_document.name
