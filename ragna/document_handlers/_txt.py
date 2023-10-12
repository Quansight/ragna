from typing import Iterator

from ragna.core import DocumentHandler, Page


class TxtDocumentHandler(DocumentHandler):
    @classmethod
    def supported_documents(cls) -> list[str]:
        return [".txt"]

    def extract_pages(self, name: str, content: bytes) -> Iterator[Page]:
        yield Page(text=content.decode())
