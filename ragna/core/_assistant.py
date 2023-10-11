import abc

import enum

from pydantic import BaseModel, Field

from ._component import RagComponent
from ._source_storage import Source


class MessageRole(enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    content: str
    role: MessageRole
    sources: list[Source] = Field(default_factory=list)

    def __str__(self):
        return self.content


class Assistant(RagComponent, abc.ABC):
    __ragna_protocol_methods__ = ["answer"]

    @property
    @abc.abstractmethod
    def max_input_size(self) -> int:
        ...

    @abc.abstractmethod
    def answer(self, prompt: str, sources: list[Source]) -> Message:
        ...
