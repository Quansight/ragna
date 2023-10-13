from __future__ import annotations

import secrets

from pathlib import Path
from typing import Literal, Union

import pydantic
import tomlkit
from pydantic import Field, ImportString
from pydantic.functional_serializers import field_serializer

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

    database_url: Union[Literal["memory"], pydantic.AnyUrl] = "memory"
    queue_url: Union[Literal["memory"], Path, pydantic.RedisDsn] = "memory"

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

    # FIXME: use the validator, but keep the value as str
    url: pydantic.HttpUrl = "http://127.0.0.1:31476"
    upload_token_secret: pydantic.SecretStr = Field(
        default_factory=lambda: secrets.token_urlsafe(64)
    )
    upload_token_ttl: int = 5 * 60

    # FIXME: https://docs.pydantic.dev/latest/examples/secrets/#serialize-secretstr-and-secretbytes-as-plain-text
    @field_serializer("upload_token_secret", when_used="json")
    def dump_secret(self, v):
        return v.get_secret_value()


class UiConfig(BaseSettings):
    class Config(ConfigBase):
        env_prefix = "ragna_ui_"

    url: pydantic.HttpUrl = "http://127.0.0.1:31476"


class Config(BaseSettings):
    class Config(ConfigBase):
        env_prefix = "ragna_"

    # FIXME: validate this to be a writeable directory or create it if it doesn't exist
    local_cache_root: Path = "~/.cache/ragna"

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
