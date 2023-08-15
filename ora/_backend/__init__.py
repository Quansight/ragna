from .component import Component
from .document import Document, DocumentMetadata, Page
from .llm import Llm
from .requirement import EnvironmentVariableRequirement, PackageRequirement, Requirement
from .source_storage import Source, SourceStorage

from . import hookspecs  # usort: skip


AVAILABLE_SPECNAMES = frozenset(
    obj.__name__
    for name, obj in hookspecs.__dict__.items()
    if callable(obj) and hasattr(obj, "ora_spec")
)
