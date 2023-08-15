from .component import Component
from .doc_db import DocDB, Source
from .doc_meta import Doc, DocMeta, Page
from .llm import LLM
from .requirement import EnvironmentVariableRequirement, PackageRequirement, Requirement

from . import hookspecs  # usort: skip


AVAILABLE_SPECNAMES = frozenset(
    obj.__name__
    for name, obj in hookspecs.__dict__.items()
    if callable(obj) and hasattr(obj, "ora_spec")
)
