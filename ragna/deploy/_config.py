from __future__ import annotations

from pathlib import Path
from typing import Type, Union

import tomlkit
from pydantic import Field, ImportString, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from ragna.core import Assistant, Document, RagnaException, SourceStorage

from ._authentication import Authentication


class ConfigBase(BaseSettings):
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # This order is needed to prioritize values from environment variables over
        # values from a configuration file. However, since the config instantiation from
        # a config file goes through the regular constructor of the Python object, we
        # are also implicitly prioritizing environment variables over values passed
        # explicitly passed to the constructor. For example, if the environment variable
        # 'RAGNA_RAG_DATABASE_URL' is set, any values passed to
        # `RagnaConfig(rag=RagConfig(database_url=...))` is ignored.
        # FIXME: Find a way to achieve the following priorities:
        #  1. Explicitly passed to Python object
        #  2. Environment variable
        #  3. Configuration file
        #  4. Default
        return env_settings, init_settings


class ComponentsConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="ragna_core_")

    source_storages: list[ImportString[type[SourceStorage]]] = [
        "ragna.source_storages.RagnaDemoSourceStorage"  # type: ignore[list-item]
    ]
    assistants: list[ImportString[type[Assistant]]] = [
        "ragna.assistants.RagnaDemoAssistant"  # type: ignore[list-item]
    ]


class ApiConfig(ConfigBase):
    # FIXME: check if we need these?
    model_config = SettingsConfigDict(env_prefix="ragna_api_")

    url: str = "http://127.0.0.1:31476"
    # FIXME: this needs to be dynamic for the UI url
    origins: list[str] = ["http://127.0.0.1:31477"]
    database_url: str = "memory"


class UiConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="ragna_ui_")

    url: str = "http://127.0.0.1:31477"
    # FIXME: this needs to be dynamic for the url
    origins: list[str] = ["http://127.0.0.1:31477"]


class Config(ConfigBase):
    """Ragna configuration"""

    model_config = SettingsConfigDict(env_prefix="ragna_")

    # FIXME: make this local root and use that as default factory
    local_cache_root: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "ragna"
    )

    document: ImportString[type[Document]] = "ragna.core.LocalDocument"  # type: ignore[assignment]

    authentication: ImportString[
        type[Authentication]
    ] = "ragna.deploy.RagnaDemoAuthentication"  # type: ignore[assignment]

    @field_validator("local_cache_root")
    @classmethod
    def _resolve_and_make_path(cls, path: Path) -> Path:
        # FIXME: move this into the util
        path = path.expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    components: ComponentsConfig = Field(default_factory=ComponentsConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    ui: UiConfig = Field(default_factory=UiConfig)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> Config:
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
