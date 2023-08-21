import abc

import dataclasses

from typing import Any

import param

from .component import Component


@dataclasses.dataclass
class ChatConfig(Component, abc.ABC):
    source_storage_name: str | param.Selector
    llm_name: str | param.Selector

    @abc.abstractmethod
    def __panel__(self):
        ...

    @abc.abstractmethod
    def get_config(self) -> tuple[str, str, dict[str, Any]]:
        ...
