from typing import Type

import pluggy

from .document import PageExtractor

from .extra_config import ChatConfig
from .llm import Llm
from .source_storage import SourceStorage


hookspec = pluggy.HookspecMarker("ragna")


@hookspec
def ragna_page_extractor() -> Type[PageExtractor]:
    """PageExtractor"""


@hookspec
def ragna_llm() -> Type[Llm]:
    """Llm"""


@hookspec
def ragna_source_storage() -> Type[SourceStorage]:
    """SourceStorage"""


@hookspec
def ragna_chat_config() -> Type[ChatConfig]:
    """ChatConfig"""
