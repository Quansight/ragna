import textwrap
import uuid

from ragna.core import Config, Document, Source, SourceStorage


class RagnaDemoSourceStorage(SourceStorage):
    """Demo assistant without requirements.

    !!! note

        As the name implies, this source storage is just for demo purposes and cannot
        retrieve relevant sources for a given prompt. It returns a single
        [ragna.core.Source][] per stored [ragna.core.Document][] with potentially
        shortened text extracted from the first [ragna.core.Page][].
    """

    @classmethod
    def display_name(cls) -> str:
        return "Ragna/DemoSourceStorage"

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._storage: dict[uuid.UUID, list[Source]] = {}

    def store(self, documents: list[Document], *, chat_id: uuid.UUID) -> None:
        self._storage[chat_id] = [
            Source(
                id=str(uuid.uuid4()),
                document=document,
                location=f"page {page.number}"
                if (page := next(document.extract_pages())).number
                else "",
                content=(content := textwrap.shorten(page.text, width=100)),
                num_tokens=len(content.split()),
            )
            for document in documents
        ]

    def retrieve(
        self, documents: list[Document], prompt: str, *, chat_id: uuid.UUID
    ) -> list[Source]:
        return self._storage[chat_id]
