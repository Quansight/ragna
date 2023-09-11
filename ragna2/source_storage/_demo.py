import json
from pathlib import Path

from ragna2.core import Document, RagnaException, Source, SourceStorage


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
            json.dump([document.name for document in documents], file)

    def retrieve(self, prompt: str, chat_id: str) -> list[Source]:
        path = self._make_path(chat_id)
        if not path.exists():
            raise RagnaException

        try:
            with open(path) as file:
                document_names = json.load(file)
        except Exception:
            raise RagnaException

        return [
            Source(
                document_name=name,
                page_numbers="N/A",
                text=(
                    text := f"I'm pretending to be a chunk of text from inside {name}."
                ),
                num_tokens=len(text.split()),
            )
            for name in document_names
        ]
