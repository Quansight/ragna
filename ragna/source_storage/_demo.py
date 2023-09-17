import json
import uuid
from pathlib import Path

from ragna.core import Document, RagnaException, Source, SourceStorage


class RagnaDemoSourceStorage(SourceStorage):
    @classmethod
    def display_name(cls):
        return "Ragna/DemoSourceStorage"

    def __init__(self, config):
        super().__init__(config)
        self._root = config.local_cache_root / "demo-source-storage"
        self._root.mkdir(exist_ok=True)

    def _make_path(self, chat_id: str) -> Path:
        return self._root / f"{chat_id}.json"

    def store(self, documents: list[Document], *, chat_id: str) -> None:
        with open(self._make_path(chat_id), "w") as file:
            json.dump([(document.id, document.name) for document in documents], file)

    def retrieve(self, prompt: str, chat_id: str) -> list[Source]:
        path = self._make_path(chat_id)
        if not path.exists():
            raise RagnaException

        try:
            with open(path) as file:
                documents = json.load(file)
        except Exception:
            raise RagnaException

        return [
            Source(
                # FIXME
                id=str(uuid.uuid4()),
                document_id=id,
                document_name=name,
                location="N/A",
                content=(
                    text := f"I pretend to be a chunk of text from inside {name} extracted by {str(self)}"
                ),
                num_tokens=len(text.split()),
            )
            for id, name in documents
        ]
