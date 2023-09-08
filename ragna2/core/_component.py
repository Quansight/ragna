import abc

import dataclasses
import functools
import inspect

from typing import Any, Optional, Protocol, Sequence

from ._requirement import Requirement


# FIXME make this a package: core, llm, source_storage, document


class Component:
    @classmethod
    def display_name(cls) -> str:
        return cls.__name__

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return []

    @classmethod
    def is_available(cls) -> bool:
        return all(requirement.is_available() for requirement in cls.requirements())

    def __init__(self, config) -> None:
        self.config = config
        self.logger = config.get_logger(name=self.display_name())

    def __str__(self) -> str:
        return self.display_name()

    __ragna_protocol_methods__: list[str]

    @functools.cache
    def _required_params(self):
        protocol_cls, protocol_methods = next(
            (cls, cls.__ragna_protocol_methods__)
            for cls in type(self).__mro__
            if "__ragna_protocol_methods__" in cls.__dict__
        )
        required = {}
        for name in protocol_methods:
            method = getattr(self, name)
            concrete_params = inspect.signature(method).parameters
            protocol_params = inspect.signature(getattr(protocol_cls, name)).parameters
            extra_params = concrete_params.keys() - protocol_params.keys()

            required[method] = {
                param
                for param in extra_params
                if concrete_params[param].default is inspect.Parameter.empty
            }
        return required


class Document(abc.ABC):
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        name: str,
        metadata: dict[str, Any],
        page_extractor=None,
    ):
        self.id = id
        self.name = name
        self.metadata = metadata
        # probably need to be a lazy import
        # FIXME we also need to check availability here as well
        # use urlsplit
        # self.page_extractor = page_extractor or _BUILTIN_PAGE_EXTRACTORS.get(
        #     Path(name).suffix
        # )

    @abc.abstractmethod
    async def read(self) -> bytes:
        ...

    async def extract_pages(self):
        async for page in self.page_extractor.extract_pages(
            name=self.name, content=await self.read()
        ):
            yield page

    @classmethod
    def _from_data(cls, data):
        return cls(id=data.id, name=data.name, metadata=data.metadata_)


class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]:
        ...

    def decode(self, tokens: Sequence[int]) -> str:
        ...


@dataclasses.dataclass
class Source:
    document_name: str
    page_numbers: str
    text: str
    num_tokens: int


class SourceStorage(Component, abc.ABC):
    __ragna_protocol_methods__ = ["store", "retrieve"]

    @abc.abstractmethod
    def store(self, documents: list[Document]) -> None:
        ...

    @abc.abstractmethod
    def retrieve(self, prompt: str) -> list[Source]:
        ...


class Llm(Component, abc.ABC):
    __ragna_protocol_methods__ = ["complete"]

    @property
    @abc.abstractmethod
    def context_size(self) -> int:
        ...

    @abc.abstractmethod
    def complete(self, prompt: str, sources: list[Source]) -> str:
        ...
