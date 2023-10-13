from __future__ import annotations

import abc
import time
import uuid
from pathlib import Path
from typing import Any, Iterator, Optional, Type, TYPE_CHECKING, TypeVar

from pydantic import BaseModel

from ._utils import PackageRequirement, RagnaException, Requirement, RequirementsMixin


if TYPE_CHECKING:
    from ._config import Config


class Document(RequirementsMixin, abc.ABC):
    @staticmethod
    def supported_suffixes() -> set[str]:
        return set(DOCUMENT_HANDLERS.keys())

    @staticmethod
    def get_handler(name: str):
        handler = DOCUMENT_HANDLERS.get(Path(name).suffix)
        if handler is None:
            raise RagnaException

        return handler

    @classmethod
    @abc.abstractmethod
    async def get_upload_info(
        cls, *, config: Config, user: str, id: uuid.UUID, name: str
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        pass

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        name: str,
        metadata: dict[str, Any],
        handler: Optional[DocumentHandler] = None,
    ):
        self.id = id
        self.name = name
        self.metadata = metadata
        self.handler = handler or self.get_handler(name)

    @abc.abstractmethod
    def is_readable(self) -> bool:
        ...

    @abc.abstractmethod
    def read(self) -> bytes:
        ...

    def extract_pages(self):
        yield from self.handler.extract_pages(self)


# FIXME: see if the S3 document is well handled
class LocalDocument(Document):
    _JWT_ALGORITHM = "HS256"

    @classmethod
    async def get_upload_info(
        cls, *, config: Config, user: str, id: uuid.UUID, name: str
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        if not PackageRequirement("PyJWT").is_available():
            raise RagnaException(
                "The package PyJWT is required to generate upload token, "
                "but is not available."
            )

        import jwt

        url = f"{config.api.url}/document"
        data = {
            "token": jwt.encode(
                payload={
                    "user": user,
                    "id": str(id),
                    "exp": time.time() + config.api.upload_token_ttl,
                },
                # FIXME: no
                key=config.api.upload_token_secret,
                algorithm=cls._JWT_ALGORITHM,
            )
        }
        metadata = {"path": str(config.local_cache_root / "documents" / str(id))}
        return url, data, metadata

    @classmethod
    def _decode_upload_token(cls, token: str, *, secret: str) -> tuple[str, uuid.UUID]:
        import jwt

        try:
            payload = jwt.decode(token, key=secret, algorithms=cls._JWT_ALGORITHM)
        except jwt.InvalidSignatureError:
            raise RagnaException(
                "Token invalid", http_status_code=401, http_detail=RagnaException.EVENT
            )
        except jwt.ExpiredSignatureError:
            raise RagnaException(
                "Token expired", http_status_code=401, http_detail=RagnaException.EVENT
            )
        return payload["user"], uuid.UUID(payload["id"])

    def __init__(
        self,
        path: Optional[str | Path] = None,
        *,
        name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs,
    ):
        if metadata is None:
            metadata = {}
        metadata_path = metadata.get("path")

        if path is None and metadata_path is None:
            raise RagnaException(
                "Path was neither passed directly or as part of the metadata"
            )
        elif path is not None and metadata_path is not None:
            raise RagnaException("Path was passed directly and as part of the metadata")
        elif path is not None:
            metadata["path"] = str(path)

        if name is None:
            name = Path(metadata["path"]).name

        super().__init__(name=name, metadata=metadata, **kwargs)

    @property
    def path(self) -> Path:
        return Path(self.metadata["path"])

    def is_readable(self) -> bool:
        return self.path.exists()

    def read(self) -> bytes:
        with open(self.path, "rb") as stream:
            return stream.read()


class Page(BaseModel):
    text: str
    number: Optional[int] = None


class DocumentHandler(RequirementsMixin, abc.ABC):
    @classmethod
    @abc.abstractmethod
    def supported_suffixes(cls) -> list[str]:
        pass

    @abc.abstractmethod
    def extract_pages(self, document: Document) -> Iterator[Page]:
        ...


T = TypeVar("T", bound=DocumentHandler)


class DocumentHandlerRegistry(dict):
    def load_if_available(self, cls: Type[T]) -> Type[T]:
        if cls.is_available():
            instance = cls()
            for suffix in cls.supported_suffixes():
                self[suffix] = instance

        return cls


DOCUMENT_HANDLERS = DocumentHandlerRegistry()


@DOCUMENT_HANDLERS.load_if_available
class TxtDocumentHandler(DocumentHandler):
    @classmethod
    def supported_suffixes(cls) -> list[str]:
        return [".txt"]

    def extract_pages(self, document: Document) -> Iterator[Page]:
        yield Page(text=document.read().decode())


@DOCUMENT_HANDLERS.load_if_available
class PdfDocumentHandler(DocumentHandler):
    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("pymupdf")]

    @classmethod
    def supported_suffixes(cls) -> list[str]:
        # TODO: pymudpdf supports a lot more formats, while .pdf is by far the most
        #  prominent. Should we expose the others here as well?
        return [".pdf"]

    def extract_pages(self, document: Document) -> Iterator[Page]:
        import fitz

        with fitz.Document(
            stream=document.read(), filetype=Path(document.name).suffix
        ) as document:
            for number, page in enumerate(document, 1):
                yield Page(text=page.get_text(sort=True), number=number)
