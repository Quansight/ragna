from pathlib import Path
from typing import Iterator

from ragna.extensions import (
    hookimpl,
    PackageRequirement,
    Page,
    PageExtractor,
    Requirement,
)


class PdfPageExtractor(PageExtractor):
    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("pymupdf")]

    # TODO: pymupdf supports a lot more formats. Check if it is useful to expose them
    #  here
    SUFFIX = ".pdf"

    def extract_pages(self, name: str, content: bytes) -> Iterator[Page]:
        import fitz

        with fitz.Document(stream=content, filetype=Path(name).suffix) as document:
            for number, page in enumerate(document, 1):
                yield Page(text=page.get_text(sort=True), number=number)


@hookimpl(specname="ragna_page_extractor")
def pdf_page_extractor():
    return PdfPageExtractor
