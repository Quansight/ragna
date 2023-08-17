from typing import Iterator

from ragna.extensions import hookimpl, Page, PageExtractor


class TxtPageExtractor(PageExtractor):
    SUFFIX = ".txt"

    def extract_pages(self, content: bytes) -> Iterator[Page]:
        yield Page(content.decode())


@hookimpl(specname="ragna_page_extractor")
def txt_page_extractor():
    return TxtPageExtractor
