from .requirement import Requirement


class Component:
    @classmethod
    def display_name(cls) -> str:
        return cls.__name__

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return []

    @classmethod
    def is_available(cls) -> bool:
        return all(requirement.is_available for requirement in cls.requirements())

    def __init__(self, app_config) -> None:
        self.app_config = app_config
