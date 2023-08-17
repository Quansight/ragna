import abc
import importlib
import importlib.metadata
import os

from functools import cached_property

import packaging.requirements


class Requirement(abc.ABC):
    @abc.abstractmethod
    @cached_property
    def is_available(self) -> bool:
        ...

    @abc.abstractmethod
    def __str__(self) -> str:
        ...


class PackageRequirement(Requirement):
    def __init__(self, requirement_string: str):
        self._requirement = packaging.requirements.Requirement(requirement_string)

    @cached_property
    def is_available(self) -> bool:
        try:
            distribution = importlib.metadata.distribution(self._requirement.name)
        except importlib.metadata.PackageNotFoundError:
            return False

        if distribution.version not in self._requirement.specifier:
            return False

        for module_name in {
            module_name
            for module_name, distribution_names in importlib.metadata.packages_distributions().items()
            if distribution.name in distribution_names
        }:
            try:
                importlib.import_module(module_name)
            except Exception:
                return False

        return True

    def __str__(self):
        return str(self._requirement)


class EnvironmentVariableRequirement(Requirement):
    def __init__(self, name):
        self._name = name

    @cached_property
    def is_available(self) -> bool:
        return self._name in os.environ

    def __str__(self):
        return self._name
