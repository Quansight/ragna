from __future__ import annotations

import abc
import time
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from ._utils import PackageRequirement, RagnaException, RagnaId, RequirementsMixin

if TYPE_CHECKING:
    from ._components import DocumentHandler
    from ._config import Config


class Document(RequirementsMixin, abc.ABC):
    def __init__(
        self,
        *,
        id: Optional[RagnaId] = None,
        name: str,
        metadata: dict[str, Any],
        handler: DocumentHandler,
    ):
        self.id = id
        self.name = name
        self.metadata = metadata
        self.handler = handler

    @classmethod
    @abc.abstractmethod
    async def get_upload_info(
        cls, *, config: Config, user: str, id: str, name: str
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        pass

    @abc.abstractmethod
    def is_readable(self) -> bool:
        ...

    @abc.abstractmethod
    def read(self) -> bytes:
        ...

    def extract_pages(self):
        yield from self.handler.extract_pages(name=self.name, content=self.read())


# FIXME: see if the S3 document is well handled
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

    _JWT_ALGORITHM = "HS256"

    @classmethod
    async def get_upload_info(
        cls, *, config: Config, user: str, id: RagnaId, name: str
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        if not PackageRequirement("PyJWT").is_available():
            raise RagnaException(
                "The package PyJWT is required to generate upload token, "
                "but is not available."
            )

        import jwt

        url = f"{config.ragna_api_url}/document/upload"
        data = {
            "token": jwt.encode(
                payload={
                    "user": user,
                    "id": str(id),
                    "exp": time.time() + config.upload_token_ttl,
                },
                # FIXME: no
                key=config.upload_token_secret,
                algorithm=cls._JWT_ALGORITHM,
            )
        }
        metadata = {"path": str(config.local_cache_root / "documents" / str(id))}
        return url, data, metadata

    @classmethod
    def _decode_upload_token(cls, token: str, *, secret: str) -> tuple[str, RagnaId]:
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
        return payload["user"], RagnaId(payload["id"])

    @property
    def path(self) -> Path:
        return Path(self.metadata["path"])

    def is_readable(self) -> bool:
        return self.path.exists()

    def read(self) -> bytes:
        with open(self.path, "rb") as stream:
            return stream.read()
