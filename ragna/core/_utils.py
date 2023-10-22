from __future__ import annotations

import abc
import enum
import functools
import importlib
import importlib.metadata
import os
from typing import Any, Collection, Union

import packaging.requirements

from ragna._compat import importlib_metadata_package_distributions


class RagnaExceptionHttpDetail(enum.Enum):
    EVENT = enum.auto()
    MESSAGE = enum.auto()


class RagnaException(Exception):
    # The values below are sentinels to be used with the http_detail field.
    # They tells the API to use the event as detail in the returned error message
    EVENT = RagnaExceptionHttpDetail.EVENT
    MESSAGE = RagnaExceptionHttpDetail.MESSAGE

    def __init__(
        self,
        # FIXME: remove default value for event
        event: str = "",
        http_status_code: int = 500,
        http_detail: Union[str, RagnaExceptionHttpDetail] = "",
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
    def is_available(self) -> bool:
        ...

    @abc.abstractmethod
    def __repr__(self) -> str:
        ...


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
            for module_name, distribution_names in importlib_metadata_package_distributions().items()
            if distribution.name in distribution_names  # type: ignore[attr-defined]
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
