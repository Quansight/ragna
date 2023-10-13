from __future__ import annotations

import abc
import datetime
import enum
import functools
import inspect
import uuid
from typing import Optional

import pydantic
import pydantic.utils

from ._document import Document

from ._utils import RagnaException, RequirementsMixin


class Component(RequirementsMixin):
    @classmethod
    def display_name(cls) -> str:
        return cls.__name__

    def __init__(self, config) -> None:
        self.config = config

    def __repr__(self) -> str:
        return self.display_name()

    # FIXME: rename this to reflect that these methods can be parametrized from the chat
    #  level
    __ragna_protocol_methods__: list[str]

    @classmethod
    @functools.cache
    def _models(cls):
        protocol_cls, protocol_methods = next(
            (cls_, cls_.__ragna_protocol_methods__)
            for cls_ in cls.__mro__
            if "__ragna_protocol_methods__" in cls_.__dict__
        )
        models = {}
        for method_name in protocol_methods:
            method = getattr(cls, method_name)
            concrete_params = inspect.signature(method).parameters
            protocol_params = inspect.signature(
                getattr(protocol_cls, method_name)
            ).parameters
            extra_param_names = concrete_params.keys() - protocol_params.keys()

            models[(cls, method_name)] = pydantic.create_model(
                f"{cls.__name__}.{method_name}",
                **{
                    (param := concrete_params[param_name]).name: (
                        param.annotation,
                        param.default
                        if param.default is not inspect.Parameter.empty
                        else ...,
                    )
                    for param_name in extra_param_names
                },
            )
        return models


class Source:
    def __init__(
        self,
        *,
        id: uuid.UUID,
        document_id: uuid.UUID,
        document_name: str,
        location: str,
        content: str,
        num_tokens: int,
    ):
        self.id = id
        self.document_id = document_id
        self.document_name = document_name
        self.location = location
        self.content = content
        self.num_tokens = num_tokens


class ReconstructedSource(Source):
    def __init__(self, **kwargs):
        if any(
            kwargs.setdefault(param, None) is not None
            for param in ["content", "num_tokens"]
        ):
            raise RagnaException
        super().__init__(**kwargs)


class SourceStorage(Component, abc.ABC):
    __ragna_protocol_methods__ = ["store", "retrieve"]

    @abc.abstractmethod
    def store(self, documents: list[Document]) -> None:
        ...

    @abc.abstractmethod
    def retrieve(self, prompt: str) -> list[Source]:
        ...


class MessageRole(enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistants"


class Message:
    def __init__(
        self,
        *,
        id: uuid.UUID,
        content: str,
        role: MessageRole,
        sources: Optional[list[Source]] = None,
    ):
        self.id = id
        self.content = content
        self.role = role
        self.sources = sources or []
        self.timestamp = datetime.datetime.utcnow()

    def __repr__(self):
        return self.content


class Assistant(Component, abc.ABC):
    __ragna_protocol_methods__ = ["answer"]

    @property
    @abc.abstractmethod
    def max_input_size(self) -> int:
        ...

    @abc.abstractmethod
    def answer(self, prompt: str, sources: list[Source]) -> Message:
        ...
