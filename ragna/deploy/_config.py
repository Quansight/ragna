from __future__ import annotations

import itertools
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Callable, Type, Union

import tomlkit
import tomlkit.container
import tomlkit.items
from pydantic import AfterValidator, Field, ImportString, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

import ragna
from ragna._utils import make_directory
from ragna.core import Assistant, Document, RagnaException, SourceStorage

from ._authentication import Authentication

if TYPE_CHECKING:
    DependentDefaultField = Any
else:

    class DependentDefaultField:
        """This class exists for a specific use case:

        - We have values for which we need the validated config to compute the default,
          e.g. the default origins can only be computed after we know the hostname and
          port.
        - We want to use the plain annotations rather than allowing a sentinel type, e.g.
          `str` vs. `Optional[str]`.

        It can be used just as `pydantic.Field` but additionally takes a callable. This
        callable gets called with the partially resolved model and should return the
        resolved value for this field it was used.
        """

        _RESERVED_PARAMS = ["default", "default_factory", "validate_default"]

        def __new__(
            cls,
            dependent_default: Callable[[DependentDefaultSettings], Any],
            **kwargs: Any,
        ) -> Field:
            if any(param in kwargs for param in cls._RESERVED_PARAMS):
                reserved_params = ", ".join(
                    repr(param) for param in cls._RESERVED_PARAMS
                )
                raise Exception(
                    f"The parameters {reserved_params} are reserved "
                    f"and cannot be passed."
                )

            self = super().__new__(cls)
            self.resolve = dependent_default
            # We are not setting 'default' here, because otherwise Pydantic tries to
            # deepcopy this object down the line.
            return Field(default_factory=lambda: self, validate_default=False)


class DependentDefaultSettings(BaseSettings):
    @model_validator(mode="after")
    def _resolve_dependent_default(self) -> DependentDefaultSettings:
        for name, info in self.model_fields.items():
            value = getattr(self, name)
            if isinstance(value, DependentDefaultField):  # type: ignore[misc]
                setattr(self, name, value.resolve(self))
        return self


class Config(DependentDefaultSettings):
    """Ragna configuration"""

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

    local_root: Annotated[Path, AfterValidator(make_directory)] = Field(
        default_factory=ragna.local_root
    )

    authentication: ImportString[type[Authentication]] = (
        "ragna.deploy.RagnaDemoAuthentication"  # type: ignore[assignment]
    )

    document: ImportString[type[Document]] = "ragna.core.LocalDocument"  # type: ignore[assignment]
    source_storages: list[ImportString[type[SourceStorage]]] = [
        "ragna.source_storages.RagnaDemoSourceStorage"  # type: ignore[list-item]
    ]
    assistants: list[ImportString[type[Assistant]]] = [
        "ragna.assistants.RagnaDemoAssistant"  # type: ignore[list-item]
    ]

    hostname: str = "127.0.0.1"
    port: int = 31476
    root_path: str = ""
    origins: list[str] = DependentDefaultField(
        lambda config: [f"http://{config.hostname}:{config.port}"]
    )

    database_url: str = DependentDefaultField(
        lambda config: f"sqlite:///{config.local_root}/ragna.db",
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

        with open(path) as file:
            return cls.model_validate(tomlkit.load(file).unwrap())

    def to_file(self, path: Union[str, Path], *, force: bool = False) -> None:
        path = Path(path).expanduser().resolve()
        if path.exists() and not force:
            raise RagnaException(f"{path} already exists.")

        with open(path, "w") as file:
            file.write(str(self))
