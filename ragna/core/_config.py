from __future__ import annotations

import secrets
from pathlib import Path
from types import ModuleType
from typing import Type, Union

import tomlkit
from pydantic import Field, ImportString, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

import ragna

from ._authentication import Authentication
from ._components import Assistant, SourceStorage
from ._document import Document
from ._utils import RagnaException


class ConfigBase:
    @classmethod
    def customise_sources(
        cls,
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # This order is needed to prioritize values from environment variables over
        # values from a configuration file. However, since the config instantiation from
        # a config file goes through the regular constructor of the Python object, we
        # are also implicitly prioritizing environment variables over values passed
        # explicitly passed to the constructor. For example, if the environment variable
        # 'RAGNA_RAG_DATABASE_URL' is set, any values passed to
        # `RagnaConfig(rag=RagConfig(database_url=...))` is ignored.
        # TODO: Find a way to achieve the following priorities:
        #  1. Explicitly passed to Python object
        #  2. Environment variable
        #  3. Configuration file
        #  4. Default
        return env_settings, init_settings


class CoreConfig(BaseSettings):
    class Config(ConfigBase):
        env_prefix = "ragna_rag_"

    queue_url: str = "memory"

    document: ImportString[type[Document]] = "ragna.core.LocalDocument"  # type: ignore[assignment]
    source_storages: list[ImportString[type[SourceStorage]]] = [
        "ragna.source_storages.RagnaDemoSourceStorage"  # type: ignore[list-item]
    ]
    assistants: list[ImportString[type[Assistant]]] = [
        "ragna.assistants.RagnaDemoAssistant"  # type: ignore[list-item]
    ]


class ApiConfig(BaseSettings):
    class Config(ConfigBase):
        env_prefix = "ragna_api_"

    url: str = "http://127.0.0.1:31476"
    database_url: str = "memory"

    authentication: ImportString[
        type[Authentication]
    ] = "ragna.core.RagnaDemoAuthentication"  # type: ignore[assignment]

    upload_token_secret: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32)[:32]
    )
    upload_token_ttl: int = 5 * 60


class UiConfig(BaseSettings):
    class Config(ConfigBase):
        env_prefix = "ragna_ui_"

    url: str = "http://127.0.0.1:31477"


class Config(BaseSettings):
    """Ragna configuration"""

    class Config(ConfigBase):
        env_prefix = "ragna_"

    local_cache_root: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "ragna"
    )

    @field_validator("local_cache_root")
    @classmethod
    def _resolve_and_make_path(cls, path: Path) -> Path:
        path = path.expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    core: CoreConfig = Field(default_factory=CoreConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    ui: UiConfig = Field(default_factory=UiConfig)

    # We need the awkward ragna.Config return annotation, because it otherwise uses the
    # Config class we have defined above. Since that needs to be removed for
    # pydantic==3, we can cleanup the annotation at the same time
    @classmethod
    def from_file(cls, path: Union[str, Path]) -> ragna.Config:
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise RagnaException(f"{path} does not exist.")

        with open(path) as file:
            return cls.model_validate(tomlkit.load(file).unwrap())

    def to_file(self, path: Union[str, Path], *, force: bool = False) -> None:
        path = Path(path).expanduser().resolve()
        if path.exists() and not force:
            raise RagnaException(f"{path} already exist.")

        with open(path, "w") as file:
            tomlkit.dump(self.model_dump(mode="json"), file)

    @classmethod
    def demo(cls) -> ragna.Config:
        return cls()

    @classmethod
    def builtin(cls) -> ragna.Config:
        from ragna import assistants, source_storages
        from ragna.core import Assistant, SourceStorage
        from ragna.core._components import Component

        def get_available_components(
            module: ModuleType, cls: Type[Component]
        ) -> list[Type]:
            return [
                obj
                for obj in module.__dict__.values()
                if isinstance(obj, type) and issubclass(obj, cls) and obj.is_available()
            ]

        config = cls()

        config.core.queue_url = str(config.local_cache_root / "queue")
        config.core.source_storages = get_available_components(
            source_storages, SourceStorage
        )
        config.core.assistants = get_available_components(assistants, Assistant)

        config.api.database_url = f"sqlite:///{config.local_cache_root}/ragna.db"

        return config
