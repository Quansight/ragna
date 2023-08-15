from typing import Type

import pluggy

from .doc_db import DocDB

from .doc_meta import DocMeta
from .llm import LLM

hookspec = pluggy.HookspecMarker("ora")


@hookspec
def ora_doc_meta() -> Type[DocMeta]:
    """doc_meta"""


@hookspec
def ora_llm() -> Type[LLM]:
    """llm"""


@hookspec
def ora_doc_db() -> Type[DocDB]:
    """doc_db"""
