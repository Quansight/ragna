from __future__ import annotations

import abc
import enum
import functools
import inspect
from typing import (
    AsyncIterable,
    AsyncIterator,
    Iterator,
    Optional,
    Type,
    Union,
    get_type_hints,
)

import pydantic
import pydantic.utils

from ._document import Document
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
        # This method dynamically builds a pydantic.BaseModel for the extra parameters
        # of each method that is listed in the __ragna_protocol_methods__ class
        # variable. These models are used by ragna.core.Chat._unpack_chat_params to
        # validate and distribute the **params passed by the user.

        # Walk up the MRO until we find the __ragna_protocol_methods__ variable. This is
        # the indicator that we found the protocol class. We use this as a reference for
        # which params of a protocol method are part of the protocol (think positional
        # parameters) and which are requested by the concrete class (think keyword
        # parameters).
        protocol_cls, protocol_methods = next(
            (cls_, cls_.__ragna_protocol_methods__)  # type: ignore[attr-defined]
            for cls_ in cls.__mro__
            if "__ragna_protocol_methods__" in cls_.__dict__
        )
        models = {}
        for method_name in protocol_methods:
            num_protocol_params = len(
                inspect.signature(getattr(protocol_cls, method_name)).parameters
            )
            method = getattr(cls, method_name)
            params = iter(inspect.signature(method).parameters.values())
            annotations = get_type_hints(method)
            # Skip over the protocol parameters in order for the model below to only
            # comprise concrete parameters.
            for _ in range(num_protocol_params):
                next(params)

            models[(cls, method_name)] = pydantic.create_model(
                # type: ignore[call-overload]
                f"{cls.__name__}.{method_name}",
                **{
                    param.name: (
                        annotations[param.name],
                        (
                            param.default
                            if param.default is not inspect.Parameter.empty
                            else ...
                        ),
                    )
                    for param in params
                },
            )
        return models

    @classmethod
    @functools.cache
    def _protocol_model(cls) -> Type[pydantic.BaseModel]:
        return merge_models(cls.display_name(), *cls._protocol_models().values())


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


class MessageRole(str, enum.Enum):
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
    def answer(self, messages: list[Message]) -> Iterator[str]:
        """Answer a prompt given the chat history.

        Args:
            messages: List of messages in the chat history. The last item is the current
                user prompt and has the relevant sources attached to it.

        Returns:
            Answer.
        """
        ...
