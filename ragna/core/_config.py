from __future__ import annotations

import secrets

from pathlib import Path
from typing import Union

import pydantic
import tomlkit
from pydantic import Field, field_validator, ImportString

from pydantic_settings import BaseSettings

from ._components import Assistant, SourceStorage
from ._document import Document

from ._utils import RagnaException


class ConfigBase:
    @classmethod
    def customise_sources(
        cls,
        init_settings: pydantic.env_settings.SettingsSourceCallable,
        env_settings: pydantic.env_settings.SettingsSourceCallable,
        file_secret_settings: pydantic.env_settings.SettingsSourceCallable,
    ) -> tuple[pydantic.env_settings.SettingsSourceCallable, ...]:
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


class RagConfig(BaseSettings):
    class Config(ConfigBase):
        env_prefix = "ragna_rag_"

    queue_url: str = "memory"

    document: ImportString[type[Document]] = "ragna.core.LocalDocument"
    source_storages: list[ImportString[type[SourceStorage]]] = [
        "ragna.source_storages.RagnaDemoSourceStorage"
    ]
    assistants: list[ImportString[type[Assistant]]] = [
        "ragna.assistants.RagnaDemoAssistant"
    ]


class ApiConfig(BaseSettings):
    class Config(ConfigBase):
        env_prefix = "ragna_api_"

    url: str = "http://127.0.0.1:31476"
    database_url: str = "memory"

    upload_token_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(64))
    upload_token_ttl: int = 5 * 60


class UiConfig(BaseSettings):
    class Config(ConfigBase):
        env_prefix = "ragna_ui_"

    url: str = "http://127.0.0.1:31477"


class Config(BaseSettings):
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

    rag: RagConfig = Field(default_factory=RagConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    ui: UiConfig = Field(default_factory=UiConfig)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> Config:
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise RagnaException

        with open(path) as file:
            return cls.model_validate(tomlkit.load(file).unwrap())

    def to_file(self, path: Union[str, Path], *, force: bool = False):
        path = Path(path).expanduser().resolve()
        if path.is_file() and not force:
            raise RagnaException

        with open(path, "w") as file:
            tomlkit.dump(self.model_dump(mode="json"), file)
