## when using API


# get-upload-info(user, name, metadata) -> (id, url, params)
# post to URL with params

# when using python

from typing import *
import abc
from pathlib import Path


_BUILTIN_PAGE_EXTRACTORS = {".pdf": None}


class Document(abc.ABC):
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        name: str,
        metadata: dict[str, Any],
        page_extractor=None,
    ):
        self.id = id
        self.name = name
        self.metadata = metadata
        # probably need to be a lazy import
        # FIXME we also need to check availability here as well
        self.page_extractor = page_extractor or _BUILTIN_PAGE_EXTRACTORS.get(
            Path(name).suffix
        )

    @abc.abstractmethod
    async def read(self) -> bytes:
        ...

    async def extract_pages(self):
        async for page in self.page_extractor.extract_pages(
            name=self.name, content=await self.read()
        ):
            yield page


# config needs to have a document_class
