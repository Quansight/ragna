from __future__ import annotations

import abc
import dataclasses
import time
from pathlib import Path
from typing import Any, Iterator, Optional, TYPE_CHECKING

from ._exceptions import RagnaException
from ._requirement import PackageRequirement, Requirement, RequirementMixin

if TYPE_CHECKING:
    from ._config import Config


class Document(abc.ABC):
    def __init__(
        self,
        *,
        id: Optional[str] = None,
        name: str,
        metadata: dict[str, Any],
        page_extractor: Optional[PageExtractor] = None,
    ):
        self.id = id
        self.name = name
        self.metadata = metadata

        if page_extractor is None:
            try:
                # FIXME:
                page_extractor = BUILTIN_PAGE_EXTRACTORS[Path(name).suffix]()
            except KeyError:
                raise RagnaException()
        self.page_extractor = page_extractor

    @classmethod
    @abc.abstractmethod
    async def get_upload_info(
        cls, *, config: Config, user: str, id: str, name: str
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        ...

    @abc.abstractmethod
    def read(self) -> bytes:
        ...

    def extract_pages(self):
        yield from self.page_extractor.extract_pages(
            name=self.name, content=self.read()
        )


class LocalDocument(Document):
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

    _JWT_ALGORITHM = "HS256"

    @classmethod
    async def get_upload_info(
        cls, *, config: Config, user: str, id: str, name: str
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        if not PackageRequirement("PyJWT").is_available():
            raise RagnaException()

        import jwt

        url = f"{config.ragna_api_url}/document/upload"
        data = {
            "token": jwt.encode(
                payload={
                    "user": user,
                    "id": id,
                    "exp": time.time() + config.upload_token_ttl,
                },
                key=config.upload_token_secret,
                algorithm=cls._JWT_ALGORITHM,
            )
        }
        metadata = {"path": str(config.local_cache_root / "documents" / id)}
        return url, data, metadata

    @classmethod
    def _decode_upload_token(cls, token: str, *, secret: str) -> tuple[str, str]:
        import jwt

        try:
            payload = jwt.decode(token, key=secret, algorithms=cls._JWT_ALGORITHM)
        except jwt.InvalidSignatureError:
            raise RagnaException
        except jwt.ExpiredSignatureError:
            raise RagnaException
        except Exception as exc:
            raise RagnaException(str(type(exc)))
        return payload["user"], payload["id"]

    @property
    def path(self) -> Path:
        return Path(self.metadata["path"])

    def is_available(self) -> bool:
        return self.path.exists()

    def read(self) -> bytes:
        with open(self.path, "rb") as stream:
            return stream.read()


@dataclasses.dataclass
class Page:
    text: str
    number: Optional[int] = None


class PageExtractor(RequirementMixin, abc.ABC):
    @abc.abstractmethod
    def extract_pages(self, name: str, content: bytes) -> Iterator[Page]:
        ...


class PageExtractors(dict):
    def register(self, suffix: str):
        def decorator(cls):
            self[suffix] = cls
            return cls

        return decorator


BUILTIN_PAGE_EXTRACTORS = PageExtractors()


@BUILTIN_PAGE_EXTRACTORS.register(".txt")
class TxtPageExtractor(PageExtractor):
    def extract_pages(self, name: str, content: bytes) -> Iterator[Page]:
        yield Page(text=content.decode())


@BUILTIN_PAGE_EXTRACTORS.register(".pdf")
class PdfPageExtractor(PageExtractor):
    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("pymupdf")]

    def extract_pages(self, name: str, content: bytes) -> Iterator[Page]:
        import fitz

        with fitz.Document(stream=content, filetype=Path(name).suffix) as document:
            for number, page in enumerate(document, 1):
                yield Page(text=page.get_text(sort=True), number=number)
