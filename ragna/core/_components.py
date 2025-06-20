from __future__ import annotations

import abc
import enum
import functools
import inspect
import uuid
from collections.abc import AsyncIterable, AsyncIterator, Iterator
from datetime import datetime, timezone
from typing import (
    Any,
    get_type_hints,
)

import pydantic
import pydantic.utils
from fastapi import status

from ._document import Document
from ._metadata_filter import MetadataFilter
from ._utils import RagnaException, RequirementsMixin, merge_models


class Component(RequirementsMixin):
    """Base class for RAG components.

    !!! tip See also

        - [ragna.core.SourceStorage][]
        - [ragna.core.Assistant][]
    """

    @classmethod
    def display_name(cls) -> str:
        """Returns Component name."""
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
    ) -> dict[tuple[type[Component], str], type[pydantic.BaseModel]]:
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
    def _protocol_model(cls) -> type[pydantic.BaseModel]:
        return merge_models(cls.display_name(), *cls._protocol_models().values())


class Source(pydantic.BaseModel):
    """Data class for sources stored inside a source storage.

    Attributes
        id: Unique ID of the source.
        document: Document this source belongs to.
        location: Location of the source inside the document.
        content: Content of the source.
        num_tokens: Number of tokens of the content.

    """

    id: str
    document_id: uuid.UUID
    document_name: str
    location: str
    content: str
    num_tokens: int

    def __hash__(self) -> int:
        return hash(self.id)


class SourceStorage(Component, abc.ABC):
    __ragna_protocol_methods__ = ["store", "retrieve"]

    @abc.abstractmethod
    def store(self, corpus_name: str, documents: list[Document]) -> None:
        """Store content of documents.

        Args:
            corpus_name: Name of the corpus to store the documents in.
            documents: Documents to store.

        """
        ...

    @abc.abstractmethod
    def retrieve(
        self, corpus_name: str, metadata_filter: MetadataFilter, prompt: str
    ) -> list[Source]:
        """Retrieve sources for a given prompt.

        Args:
            corpus_name: Name of the corpus to retrieve sources from.
            metadata_filter: Filter to select available sources.
            prompt: Prompt to retrieve sources for.

        Returns:
            Matching sources for the given prompt ordered by relevance.

        """
        ...

    def list_corpuses(self) -> list[str]:
        """List available corpuses.

        Returns
            List of available corpuses.

        """
        raise RagnaException(
            "list_corpuses is not implemented",
            source_storage=self.__class__.display_name(),
            http_status_code=status.HTTP_400_BAD_REQUEST,
            http_detail=RagnaException.MESSAGE,
        )

    def list_metadata(
        self, corpus_name: str | None = None
    ) -> dict[str, dict[str, tuple[str, list[Any]]]]:
        """List available metadata for corpuses.

        Args:
            corpus_name: Only return metadata for this corpus.

        Returns:
            List of available metadata.

        """
        raise RagnaException(
            "list_metadata is not implemented",
            source_storage=self.__class__.display_name(),
            http_status_code=status.HTTP_400_BAD_REQUEST,
            http_detail=RagnaException.MESSAGE,
        )


class MessageRole(str, enum.Enum):
    """Message role

    Attributes
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

    Attributes
        role: The message producer.
        sources: The sources used to produce the message.

    !!! tip "See also"

        - [ragna.core.Chat.prepare][]
        - [ragna.core.Chat.answer][]

    """

    def __init__(
        self,
        content: str | AsyncIterable[str],
        *,
        role: MessageRole = MessageRole.SYSTEM,
        sources: list[Source] | None = None,
        id: uuid.UUID | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        if isinstance(content, str):
            self._content: str = content
        else:
            self._content_stream: AsyncIterable[str] = content

        self.role = role
        self.sources = sources or []

        if id is None:
            id = uuid.uuid4()
        self.id = id

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        self.timestamp = timestamp

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

    @classmethod
    def avatar(cls) -> str:
        """Return a default avatar for an assistant in a chat."""
        return cls.display_name().split("/")[-1][0].upper()
