from typing import Type

import pluggy

from .document import DocumentMetadata
from .llm import Llm

from .source_storage import SourceStorage

hookspec = pluggy.HookspecMarker("ora")


@hookspec
def ora_document_metadata() -> Type[DocumentMetadata]:
    """DocumentMetadata"""


@hookspec
def ora_llm() -> Type[Llm]:
    """Llm"""


@hookspec
def ora_source_storage() -> Type[SourceStorage]:
    """SourceStorage"""
