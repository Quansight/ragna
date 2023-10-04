import textwrap
from typing import Any

from ragna.core import Document, RagnaId, Source, SourceStorage


class RagnaDemoSourceStorage(SourceStorage):
    @classmethod
    def display_name(cls):
        return "Ragna/DemoSourceStorage"

    def __init__(self, config):
        super().__init__(config)
        self._storage: dict[RagnaId, Any] = {}

    def store(self, documents: list[Document], *, chat_id: RagnaId) -> None:
        self._storage[chat_id] = [
            {
                "document_id": str(document.id),
                "document_name": document.name,
                "location": f"page {page.number}"
                if (page := next(document.extract_pages())).number
                else "",
                "content": (content := textwrap.shorten(page.text, width=100)),
                "num_tokens": len(content.split()),
            }
            for document in documents
        ]

    def retrieve(self, prompt: str, *, chat_id: RagnaId) -> list[Source]:
        return [
            Source(
                id=RagnaId.make(),
                document_id=RagnaId(source["document_id"]),
                document_name=source["document_name"],
                location=source["location"],
                content=source["content"],
                num_tokens=source["num_tokens"],
            )
            for source in self._storage[chat_id]
        ]
