import abc

from .requirement import Requirement


class Component(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        ...

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return []

    @classmethod
    def is_available(cls) -> bool:
        return all(requirement.is_available for requirement in cls.requirements())
