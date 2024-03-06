from __future__ import annotations

import itertools
from pathlib import Path
from typing import Annotated, Any, Callable, Generic, Type, TypeVar, Union

import tomlkit
import tomlkit.container
import tomlkit.items
from pydantic import (
    AfterValidator,
    Field,
    ImportString,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

import ragna
from ragna._utils import make_directory
from ragna.core import Assistant, Document, RagnaException, SourceStorage

from ._authentication import Authentication

T = TypeVar("T")


class AfterConfigValidateDefault(Generic[T]):
    """This class exists for a specific use case:

    - We have values for which we need the validated config to compute the default,
      e.g. the API default origins can only be computed after we know the UI hostname
      and port.
    - We want to use the plain annotations rather than allowing a sentinel type, e.g.
      `str` vs. `Optional[str]`.
    """

    def __init__(self, make_default: Callable[[Config], T]) -> None:
        self.make_default = make_default

    @classmethod
    def make(cls, make_default: Callable[[Config], T]) -> Any:
        """Creates a default sentinel that is resolved after the config is validated.

        Args:
            make_default: Callable that takes the validated config and returns the
                resolved value.
        """
        return Field(default=cls(make_default), validate_default=False)


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
        # 'RAGNA_LOCAL_ROOT' is set, any values passed to `Config(local_root=...)` are
        # ignored.
        # FIXME: Find a way to achieve the following priorities:
        #  1. Explicitly passed to Python object
        #  2. Environment variable
        #  3. Configuration file
        #  4. Default
        return env_settings, init_settings

    def _resolve_default_sentinels(self, config: Config) -> None:
        for name, info in self.model_fields.items():
            value = getattr(self, name)
            if isinstance(value, ConfigBase):
                value._resolve_default_sentinels(config)
            elif isinstance(value, AfterConfigValidateDefault):
                setattr(self, name, value.make_default(config))

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


def make_default_origins(config: Config) -> list[str]:
    return [f"http://{config.ui.hostname}:{config.ui.port}"]


class ApiConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="ragna_api_")

    hostname: str = "127.0.0.1"
    port: int = 31476
    root_path: str = ""
    url: str = AfterConfigValidateDefault.make(
        lambda config: f"http://{config.api.hostname}:{config.api.port}{config.api.root_path}",
    )
    database_url: str = AfterConfigValidateDefault.make(
        lambda config: f"sqlite:///{config.local_root}/ragna.db",
    )
    origins: list[str] = AfterConfigValidateDefault.make(make_default_origins)


class UiConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="ragna_ui_")

    hostname: str = "127.0.0.1"
    port: int = 31477
    origins: list[str] = AfterConfigValidateDefault.make(make_default_origins)


class Config(ConfigBase):
    """Ragna configuration"""

    model_config = SettingsConfigDict(env_prefix="ragna_")

    local_root: Annotated[Path, AfterValidator(make_directory)] = Field(
        default_factory=ragna.local_root
    )

    authentication: ImportString[
        type[Authentication]
    ] = "ragna.deploy.RagnaDemoAuthentication"  # type: ignore[assignment]

    document: ImportString[type[Document]] = "ragna.core.LocalDocument"  # type: ignore[assignment]
    source_storages: list[ImportString[type[SourceStorage]]] = [
        "ragna.source_storages.RagnaDemoSourceStorage"  # type: ignore[list-item]
    ]
    assistants: list[ImportString[type[Assistant]]] = [
        "ragna.assistants.RagnaDemoAssistant"  # type: ignore[list-item]
    ]

    api: ApiConfig = Field(default_factory=ApiConfig)
    ui: UiConfig = Field(default_factory=UiConfig)

    @model_validator(mode="after")
    def _validate_model(self) -> Config:
        self._resolve_default_sentinels(self)
        return self

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
            raise RagnaException(f"{path} already exists.")

        with open(path, "w") as file:
            file.write(str(self))
