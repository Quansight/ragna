from __future__ import annotations

import abc
import enum
import functools
import inspect
import itertools
import warnings
from collections import deque
from typing import (
    AsyncIterable,
    AsyncIterator,
    Iterator,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints, TypeVar, Iterable, Deque, cast,
)
from uuid import UUID

from dataclasses import dataclass

import pydantic
import pydantic.utils

from abc import ABC, abstractmethod

from ragna._compat import itertools_pairwise

from ._document import Document, Chunk, Page
from ._utils import RequirementsMixin, merge_models


class Component(RequirementsMixin):
    """Base class for RAG components.

    !!! tip See also

        - [ragna.core.SourceStorage][]
        - [ragna.core.Assistant][]
    """

    @classmethod
    def display_name(cls) -> str:
        """
        Returns:
            Component name.
        """
        return cls.__name__

    def __repr__(self) -> str:
        return self.display_name()

    # FIXME: rename this to reflect that these methods can be parametrized from the chat
    #  level
    __ragna_protocol_methods__: list[str]

    @classmethod
    @functools.cache
    def _protocol_models(
        cls,
    ) -> dict[tuple[Type[Component], str], Type[pydantic.BaseModel]]:
        protocol_cls, protocol_methods = next(
            (cls_, cls_.__ragna_protocol_methods__)  # type: ignore[attr-defined]
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

            models[(cls, method_name)] = pydantic.create_model(  # type: ignore[call-overload]
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

    @classmethod
    @functools.cache
    def _protocol_model(cls) -> Type[pydantic.BaseModel]:
        return merge_models(cls.display_name(), *cls._protocol_models().values())


@dataclass
class Embedding:
    embedding: list[float]
    chunk: Chunk


T = TypeVar("T")


# The function is adapted from more_itertools.windowed to allow a ragged last window
# https://more-itertools.readthedocs.io/en/stable/api.html#more_itertools.windowed
def _windowed_ragged(
    iterable: Iterable[T], *, n: int, step: int
) -> Iterator[tuple[T, ...]]:
    window: Deque[T] = deque(maxlen=n)
    i = n
    for _ in map(window.append, iterable):
        i -= 1
        if not i:
            i = step
            yield tuple(window)

    if len(window) < n:
        yield tuple(window)
    elif 0 < i < min(step, n):
        yield tuple(window)[i:]


class EmbeddingModel(Component, ABC):
    _EMBEDDING_DIMENSIONS: int
    def __init__(self):
        import tiktoken
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def _chunk_pages(
            self, pages: Iterable[Page], document_id: UUID, *, chunk_size: int, chunk_overlap: int
    ) -> Iterator[Chunk]:
        for window in _windowed_ragged(
                (
                        (tokens, page.number)
                        for page in pages
                        for tokens in self._tokenizer.encode(page.text)
                ),
                n=chunk_size,
                step=chunk_size - chunk_overlap,
        ):
            tokens, page_numbers = zip(*window)
            yield Chunk(
                text=self._tokenizer.decode(tokens),  # type: ignore[arg-type]
                document_id=document_id,
                page_numbers=list(filter(lambda n: n is not None, page_numbers))
                             or None,
                num_tokens=len(tokens),
            )

    @classmethod
    def _page_numbers_to_str(cls, page_numbers: Optional[Iterable[int]]) -> str:
        if not page_numbers:
            return ""

        page_numbers = sorted(set(page_numbers))
        if len(page_numbers) == 1:
            return str(page_numbers[0])

        ranges_str = []
        range_int = []
        for current_page_number, next_page_number in itertools_pairwise(
                itertools.chain(sorted(page_numbers), [None])
        ):
            current_page_number = cast(int, current_page_number)

            range_int.append(current_page_number)
            if next_page_number is None or next_page_number > current_page_number + 1:
                ranges_str.append(
                    ", ".join(map(str, range_int))
                    if len(range_int) < 3
                    else f"{range_int[0]}-{range_int[-1]}"
                )
                range_int = []

        return ", ".join(ranges_str)

    @classmethod
    def _take_sources_up_to_max_tokens(
            cls, sources: Iterable[Source], *, max_tokens: int
    ) -> list[Source]:
        taken_sources = []
        total = 0
        for source in sources:
            new_total = total + source.num_tokens
            if new_total > max_tokens:
                break

            taken_sources.append(source)
            total = new_total

        return taken_sources

    @abstractmethod
    def embed_chunks(self, chunks: list[Chunk]) -> list[Embedding]:
        ...

    def embed_text(self, text: str) -> list[float]:
        ...


class Source(pydantic.BaseModel):
    """Data class for sources stored inside a source storage.

    Attributes:
        id: Unique ID of the source.
        document: Document this source belongs to.
        location: Location of the source inside the document.
        content: Content of the source.
        num_tokens: Number of tokens of the content.
    """

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    id: str
    document: Document
    location: str
    content: str
    num_tokens: int


class SourceStorage(Component, abc.ABC):
    __ragna_protocol_methods__ = ["store", "retrieve"]
    __ragna_input_type__: Union[Document, Embedding]

    def __init_subclass__(cls):
        if inspect.isabstract(cls):
            return

        valid_input_types = get_args(get_type_hints(cls)["__ragna_input_type__"])

        input_parameter_name = list(inspect.signature(cls.store).parameters.keys())[1]
        input_parameter_annotation = get_type_hints(cls.store).get(input_parameter_name)

        if input_parameter_annotation is None:
            input_type = None
        else:

            def extract_input_type():
                origin = get_origin(input_parameter_annotation)
                if origin is None:
                    return None

                args = get_args(input_parameter_annotation)
                if len(args) != 1:
                    return None

                input_type = args[0]
                if not issubclass(input_type, valid_input_types):
                    return None

                return input_type

            input_type = extract_input_type()

        if input_type is None:
            warnings.warn("ADDME")
            input_type = Document

        cls.__ragna_input_type__ = input_type

    @abc.abstractmethod
    def store(self, documents: list[Document]) -> None:
        """Store content of documents.

        Args:
            documents: Documents to store.
        """
        ...

    @abc.abstractmethod
    def retrieve(self, documents: list[Document], prompt: str) -> list[Source]:
        """Retrieve sources for a given prompt.

        Args:
            documents: Documents to retrieve sources from.
            prompt: Prompt to retrieve sources for.

        Returns:
            Matching sources for the given prompt ordered by relevance.
        """
        ...


class MessageRole(enum.Enum):
    """Message role

    Attributes:
        SYSTEM: The message was produced by the system. This includes the welcome
            message when [preparing a new chat][ragna.core.Chat.prepare] as well as
            error messages.
        USER: The message was produced by the user.
        ASSISTANT: The message was produced by an assistant.
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message:
    """Data class for messages.

    Attributes:
        role: The message producer.
        sources: The sources used to produce the message.

    !!! tip "See also"

        - [ragna.core.Chat.prepare][]
        - [ragna.core.Chat.answer][]
    """

    def __init__(
        self,
        content: Union[str, AsyncIterable[str]],
        *,
        role: MessageRole = MessageRole.SYSTEM,
        sources: Optional[list[Source]] = None,
    ) -> None:
        if isinstance(content, str):
            self._content: str = content
        else:
            self._content_stream: AsyncIterable[str] = content

        self.role = role
        self.sources = sources or []

    async def __aiter__(self) -> AsyncIterator[str]:
        if hasattr(self, "_content"):
            yield self._content
            return

        chunks = []
        async for chunk in self._content_stream:
            chunks.append(chunk)
            yield chunk

        self._content = "".join(chunks)

    async def read(self) -> str:
        if not hasattr(self, "_content"):
            # Since self.__aiter__ is already setting the self._content attribute, we
            # only need to exhaust the content stream here.
            async for _ in self:
                pass
        return self._content

    @property
    def content(self) -> str:
        if not hasattr(self, "_content"):
            raise RuntimeError(
                "Message content cannot be accessed without having iterated over it, "
                "e.g. `async for chunk in message`, or reading the content, e.g. "
                "`await message.read()`, first."
            )
        return self._content

    def __str__(self) -> str:
        return self.content

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"content={self.content}, role={self.role}, sources={self.sources}"
            f")"
        )


class Assistant(Component, abc.ABC):
    """Abstract base class for assistants used in [ragna.core.Chat][]"""

    __ragna_protocol_methods__ = ["answer"]

    @abc.abstractmethod
    def answer(self, prompt: str, sources: list[Source]) -> Iterator[str]:
        """Answer a prompt given some sources.

        Args:
            prompt: Prompt to be answered.
            sources: Sources to use when answering answer the prompt.

        Returns:
            Answer.
        """
        ...
