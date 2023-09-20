from __future__ import annotations

import dataclasses

import importlib.util

import inspect

import logging

import secrets
import sys
from pathlib import Path

from typing import Type

import structlog

from ._assistant import Assistant

from ._component import RagComponent
from ._core import RagnaException
from ._document import Document, LocalDocument
from ._source_storage import SourceStorage


@dataclasses.dataclass
class Config:
    state_database_url: str = dataclasses.field(default=None)
    queue_database_url: str = "redis://127.0.0.1:6379"
    ragna_api_url: str = "http://127.0.0.1:31476"
    ragna_ui_url: str = "http://127.0.0.1:31477"

    local_cache_root: Path = Path.home() / ".cache" / "ragna"

    document_class: Type[Document] = LocalDocument
    upload_token_secret: str = dataclasses.field(default_factory=secrets.token_hex)
    upload_token_ttl: int = 30

    registered_source_storage_classes: dict[
        str, Type[SourceStorage]
    ] = dataclasses.field(default_factory=dict)
    registered_assistant_classes: dict[str, Type[Assistant]] = dataclasses.field(
        default_factory=dict
    )

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

    @staticmethod
    def load_from_source(source: str) -> Config:
        name = None
        parts = source.split("::")
        if len(parts) == 2:
            source, name = parts
        elif len(parts) != 1:
            raise RagnaException

        path = Path(source).expanduser().resolve()
        if path.exists():
            spec = importlib.util.spec_from_file_location(path.name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            try:
                module = importlib.import_module(source)
            except ModuleNotFoundError:
                source, name = source.rsplit(".", 1)
                module = importlib.import_module(source)

        return getattr(module, name or "config")

    def register_component(self, cls):
        if not (
            isinstance(cls, type)
            and issubclass(cls, RagComponent)
            and not inspect.isabstract(cls)
        ):
            raise RagnaException()
        if issubclass(cls, SourceStorage):
            registry = self.registered_source_storage_classes
        elif issubclass(cls, Assistant):
            registry = self.registered_assistant_classes
        else:
            raise RagnaException

        registry[cls.display_name()] = cls

        return cls

    def get_logger(self, **initial_values):
        human_readable = sys.stderr.isatty()

        processors = [
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
        ]
        if human_readable:
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
