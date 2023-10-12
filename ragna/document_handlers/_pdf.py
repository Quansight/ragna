from pathlib import Path

from typing import Iterator

from ragna.core import DocumentHandler, PackageRequirement, Page, Requirement


class PdfDocumentHandler(DocumentHandler):
    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("pymupdf")]

    @classmethod
    def supported_documents(cls) -> list[str]:
        # TODO: pymudpdf supports a lot more formats, while .pdf is by far the most
        #  prominent. Should we expose the others here as well?
        return [".pdf"]

    def extract_pages(self, name: str, content: bytes) -> Iterator[Page]:
        import fitz

        with fitz.Document(stream=content, filetype=Path(name).suffix) as document:
            for number, page in enumerate(document, 1):
                yield Page(text=page.get_text(sort=True), number=number)
