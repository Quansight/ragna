from __future__ import annotations

import itertools
from pathlib import Path
from typing import Annotated, ClassVar, Type, Union, cast

import tomlkit
import tomlkit.container
import tomlkit.items
from pydantic import AfterValidator, Field, ImportString
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

import ragna
from ragna._utils import make_directory
from ragna.core import Assistant, Document, RagnaException, SourceStorage

from ._auth import Auth
from ._key_value_store import KeyValueStore


class Config(BaseSettings):
    """Ragna configuration"""

    __config_path__: ClassVar[Path | None] = None

    model_config = SettingsConfigDict(env_prefix="ragna_")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources = [init_settings, env_settings]
        if cls.__config_path__ is not None:
            sources.append(
                TomlConfigSettingsSource(settings_cls, toml_file=cls.__config_path__)
            )
        return tuple(sources)

    local_root: Annotated[Path, AfterValidator(make_directory)] = Field(
        default_factory=ragna.local_root
    )

    auth: ImportString[type[Auth]] = Field(
        default="ragna.deploy.NoAuth", validate_default=True
    )  # type: ignore[assignment]
    key_value_store: ImportString[type[KeyValueStore]] = Field(
        default="ragna.deploy.InMemoryKeyValueStore", validate_default=True
    )  # type: ignore[assignment]

    document: ImportString[type[Document]] = Field(
        default="ragna.core.LocalDocument", validate_default=True
    )  # type: ignore[assignment]
    source_storages: list[ImportString[type[SourceStorage]]] = Field(
        default_factory=lambda: ["ragna.source_storages.RagnaDemoSourceStorage"],  # type: ignore[arg-type]
        validate_default=True,
    )
    assistants: list[ImportString[type[Assistant]]] = Field(
        default_factory=lambda: ["ragna.assistants.RagnaDemoAssistant"],  # type: ignore[arg-type]
        validate_default=True,
    )

    hostname: str = "127.0.0.1"
    port: int = 31476
    root_path: str = ""
    origins: list[str] = Field(
        default_factory=lambda values: [f"http://{values['hostname']}:{values['port']}"]
    )
    session_lifetime: int = 60 * 60 * 24

    database_url: str = Field(
        default_factory=lambda values: f"sqlite:///{values['local_root']}/ragna.db"
    )

    @property
    def _url(self) -> str:
        return f"http://{self.hostname}:{self.port}{self.root_path}"

    def __str__(self) -> str:
        toml = tomlkit.item(self.model_dump(mode="json"))
        self._set_multiline_array(toml)
        return toml.as_string()

    def _set_multiline_array(self, item: tomlkit.items.Item) -> None:
        if isinstance(item, tomlkit.items.Array):
            item.multiline(True)

        if not isinstance(item, tomlkit.items.Table):
            return

        container = item.value
        for child in itertools.chain(
            (value for _, value in container.body), container.value.values()
        ):
            self._set_multiline_array(child)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> Config:
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise RagnaException(f"{path} does not exist.")

        return cast(
            type[Config], type(cls.__name__, (cls,), {"__config_path__": path})
        )()

    def to_file(self, path: Union[str, Path], *, force: bool = False) -> None:
        path = Path(path).expanduser().resolve()
        if path.exists() and not force:
            raise RagnaException(f"{path} already exists.")

        with open(path, "w") as file:
            file.write(str(self))
