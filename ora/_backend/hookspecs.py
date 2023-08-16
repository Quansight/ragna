from typing import Type

import pluggy

from .document import PageExtractor
from .llm import Llm

from .source_storage import SourceStorage

hookspec = pluggy.HookspecMarker("ora")


@hookspec
def ora_page_extractor() -> Type[PageExtractor]:
    """PageExtractor"""


@hookspec
def ora_llm() -> Type[Llm]:
    """Llm"""


@hookspec
def ora_source_storage() -> Type[SourceStorage]:
    """SourceStorage"""
