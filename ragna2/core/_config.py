from __future__ import annotations

import dataclasses

import inspect

import logging
import sys
from pathlib import Path

from typing import Any, Optional, Type, Union

import structlog

from ._component import Component, Document, Llm, SourceStorage
from ._exceptions import RagnaException


class LocalDocument(Document):
    def __init__(
        self,
        path: Optional[Union[str | Path]] = None,
        *,
        name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs,
    ):
        if metadata is None:
            metadata = {}
        metadata_path = metadata.get("path")

        if path is None and metadata_path is None:
            raise RagnaException()
        elif path is not None and metadata_path is not None:
            raise RagnaException()
        elif metadata_path is not None:
            path = metadata_path
        else:
            metadata["path"] = str(path)
        if name is None:
            name = Path(path).name
        super().__init__(name=name, metadata=metadata, **kwargs)

    @property
    def path(self) -> Path:
        return Path(self.metadata["path"])

    async def read(self) -> bytes:
        # FIXME: check if aiofiles is available. if so, use that
        with open(self.path, "rb") as stream:
            return stream.read()


@dataclasses.dataclass
class Config:
    local_cache_root: Path = Path.home() / ".cache" / "ragna"
    state_database_url: str = dataclasses.field(default=None)
    queue_database_url: str = "redis://127.0.0.1:6379"
    source_storage_classes: dict[str, Type[SourceStorage]] = dataclasses.field(
        default_factory=dict
    )
    llm_classes: dict[str, Type[Llm]] = dataclasses.field(default_factory=dict)
    document_class = LocalDocument

    def __post_init__(self):
        self.local_cache_root = self._parse_local_cache_root(self.local_cache_root)

        if self.state_database_url is None:
            self.state_database_url = f"sqlite:///{self.local_cache_root / 'ragna.db'}"

    def _parse_local_cache_root(self, path):
        if not isinstance(path, Path):
            path = Path(path)
        path = path.expanduser().resolve()

        # FIXME: refactor this
        if path.exists():
            if not path.is_dir():
                raise RagnaException()
            elif not self._is_writable(path):
                raise RagnaException
        else:
            try:
                path.mkdir(parents=True)
            except Exception:
                raise RagnaException from None

        return path

    def _is_writable(self, path):
        # FIXME: implement this
        return True

    def register_component(self, cls):
        if not (
            isinstance(cls, type)
            and issubclass(cls, Component)
            and not inspect.isabstract(cls)
        ):
            raise RagnaException()
        if issubclass(cls, SourceStorage):
            registry = self.source_storage_classes
        elif issubclass(cls, Llm):
            registry = self.llm_classes
        else:
            raise RagnaException

        registry[cls.display_name()] = cls

        return cls

    def get_logger(self, **initial_values):
        dev_friendly = sys.stderr.isatty()

        processors = [
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.PATHNAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
        ]
        if dev_friendly:
            processors.extend(
                [
                    structlog.processors.ExceptionPrettyPrinter(),
                    structlog.dev.ConsoleRenderer(),
                ]
            )
        else:
            processors.extend(
                [
                    structlog.processors.dict_tracebacks,
                    structlog.processors.JSONRenderer(),
                ]
            )

        return structlog.wrap_logger(
            logger=structlog.PrintLogger(),
            cache_logger_on_first_use=True,
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            processors=processors,
            **initial_values,
        )
