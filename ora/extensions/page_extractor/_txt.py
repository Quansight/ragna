from ora.extensions import hookimpl, Page, PageExtractor


class TxtPageExtractor(PageExtractor):
    SUFFIX = ".txt"

    def extract_pages(self, content: bytes) -> list[Page]:
        return [Page(content.decode())]


@hookimpl(specname="ora_page_extractor")
def txt_page_extractor():
    return TxtPageExtractor
