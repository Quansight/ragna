from __future__ import annotations

import abc
import enum
import functools
import importlib
import importlib.metadata
import os
from collections import defaultdict
from collections.abc import Collection
from typing import Any, cast

import packaging.requirements
import pydantic
import pydantic_core

packages_distributions = functools.cache(importlib.metadata.packages_distributions)


class RagnaExceptionHttpDetail(enum.Enum):
    EVENT = enum.auto()
    MESSAGE = enum.auto()


class RagnaException(Exception):
    """Ragna exception."""

    # The values below are sentinels to be used with the http_detail field.
    # They tells the API to use the event as detail in the returned error message
    EVENT = RagnaExceptionHttpDetail.EVENT
    MESSAGE = RagnaExceptionHttpDetail.MESSAGE

    def __init__(
        self,
        # FIXME: remove default value for event
        event: str = "",
        http_status_code: int = 500,
        http_detail: str | RagnaExceptionHttpDetail = "",
        **extra: Any,
    ) -> None:
        self.event = event
        self.http_status_code = http_status_code
        self.http_detail = http_detail
        self.extra = extra

    def __str__(self) -> str:
        return ", ".join([self.event, *[f"{k}={v}" for k, v in self.extra.items()]])


class Requirement(abc.ABC):
    @abc.abstractmethod
    def is_available(self) -> bool: ...

    @abc.abstractmethod
    def __repr__(self) -> str: ...

    def __hash__(self) -> int:
        return hash(repr(self))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Requirement):
            return NotImplemented

        return repr(self) == repr(other)


class RequirementsMixin:
    @classmethod
    def requirements(cls) -> list[Requirement]:
        return []

    @classmethod
    def is_available(cls) -> bool:
        return all(requirement.is_available() for requirement in cls.requirements())


class PackageRequirement(Requirement):
    def __init__(
        self, requirement_string: str, *, exclude_modules: Collection[str] = ()
    ) -> None:
        self._requirement = packaging.requirements.Requirement(requirement_string)
        self._exclude_modules = set(exclude_modules)

    @functools.cache
    def is_available(self) -> bool:
        try:
            distribution = importlib.metadata.distribution(self._requirement.name)
        except importlib.metadata.PackageNotFoundError:
            return False

        if distribution.version not in self._requirement.specifier:
            return False

        for module_name in {
            module_name
            for module_name, distribution_names in packages_distributions().items()
            if distribution.name in distribution_names
            and module_name not in self._exclude_modules
        }:
            try:
                importlib.import_module(module_name)
            except Exception:
                return False

        return True

    def __repr__(self) -> str:
        return str(self._requirement)


class EnvVarRequirement(Requirement):
    def __init__(self, name: str) -> None:
        self._name = name

    @functools.cache
    def is_available(self) -> bool:
        return self._name in os.environ

    def __repr__(self) -> str:
        return self._name


def merge_models(
    model_name: str,
    *models: type[pydantic.BaseModel],
    config: pydantic.ConfigDict | None = None,
) -> type[pydantic.BaseModel]:
    raw_field_definitions = defaultdict(list)
    for model_cls in models:
        for name, field in model_cls.__pydantic_fields__.items():
            type_ = field.annotation

            default: Any
            if field.is_required():
                default = ...
            elif field.default is pydantic_core.PydanticUndefined:
                default = ("default_factory", field.default_factory)
            else:
                default = ("default", field.default)

            raw_field_definitions[name].append((type_, default))

    field_definitions = {}
    for name, definitions in raw_field_definitions.items():
        types, defaults = zip(*definitions, strict=False)

        types = set(types)
        if len(types) > 1:
            raise RagnaException(f"Mismatching types for field {name}: {types}")
        type_ = types.pop()

        defaults = set(defaults)
        kwargs: dict[str, Any]
        if ... in defaults:
            kwargs = {}
        elif len(defaults) == 1:
            kwargs = dict(defaults)
        else:
            kwargs = {"default": None}

        field_definitions[name] = (type_, pydantic.Field(**kwargs))

    return cast(
        type[pydantic.BaseModel],
        pydantic.create_model(  # type: ignore[call-overload]
            model_name, **field_definitions, __config__=config
        ),
    )
