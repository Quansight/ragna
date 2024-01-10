from __future__ import annotations

import datetime
import functools
import inspect
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

import anyio
import pydantic

from ._components import Assistant, Component, Message, MessageRole, SourceStorage
from ._document import Document, LocalDocument
from ._utils import RagnaException, default_user, merge_models

T = TypeVar("T")
C = TypeVar("C", bound=Component)


async def _run(
    fn: Callable[..., Union[T, Awaitable[T]]], *args: Any, **kwargs: Any
) -> T:
    if inspect.iscoroutinefunction(fn):
        fn = cast(Callable[..., Awaitable[T]], fn)
        return await fn(*args, **kwargs)
    else:
        fn = cast(Callable[..., T], fn)
        return await anyio.to_thread.run_sync(functools.partial(fn, *args, **kwargs))


class Rag(Generic[C]):
    """RAG workflow."""

    def __init__(self) -> None:
        self._components: dict[Type[C], C] = {}

    def _load_component(self, component: Union[Type[C], C]) -> C:
        cls: Type[C]
        instance: Optional[C]

        if isinstance(component, Component):
            instance = cast(C, component)
            cls = type(instance)
        elif isinstance(component, type) and issubclass(component, Component):
            cls = component
            instance = None
        else:
            raise RagnaException

        if cls not in self._components:
            if instance is None:
                if not cls.is_available():
                    raise RagnaException(
                        "Component not available", name=cls.display_name()
                    )
                instance = cls()

            self._components[cls] = instance

        return self._components[cls]

    def corpus(
        self,
        *,
        documents: Iterable[Any],
        source_storage: Union[Type[SourceStorage], SourceStorage],
        corpus_name: str,
        **params: Any,
    ) -> Corpus:
        """Create a new [ragna.core.Corpus][].

        Args:
            documents: Documents to use.
            source_storage: Source storage to use.
            corpus_name: Name of the corpus.
            **params: Additional parameters passed to the source storage.
        """
        return Corpus(
            self,
            documents=documents,
            source_storage=source_storage,
            corpus_name=corpus_name,
            **params,
        )

    def chat(
        self,
        *,
        corpus: Corpus,
        assistant: Union[Type[Assistant], Assistant],
        **params: Any,
    ) -> Chat:
        """Create a new [ragna.core.Chat][].

        Args:
            corpus: Corpus to use.
            assistant: Assistant to use.
            **params: Additional parameters passed to the assistant.
        """
        return Chat(
            self,
            corpus=corpus,
            assistant=assistant,
            **params,
        )


class Corpus:
    """
    !!! tip

        This object is usually not instantiated manually, but rather through
        [ragna.core.Rag.corpus][].

        Args:
        rag: The RAG workflow this corpus is associated with.
        documents: Documents to use.
        source_storage: Source storage to use.
        **params: Additional parameters passed to the source storage.
    """

    def __init__(
        self,
        rag: Rag,
        *,
        documents: Iterable[Any],
        source_storage: Union[Type[SourceStorage], SourceStorage],
        corpus_name: str,
        **params: Any,
    ) -> None:
        self._rag = rag

        self.documents = self._parse_documents(documents)
        self.source_storage = self._rag._load_component(source_storage)
        self.corpus_name = corpus_name
        self.params = params

    async def prepare(self) -> None:
        """Prepare the documents."""
        await _run(
            self.source_storage.store,
            self.documents,
            corpus_name=self.corpus_name,
            **self.params,
        )

    def _parse_documents(self, documents: Iterable[Any]) -> list[Document]:
        documents_ = []
        for document in documents:
            if not isinstance(document, Document):
                document = LocalDocument.from_path(document)

            if not document.is_readable():
                raise RagnaException(
                    "Document not readable",
                    document=document,
                    http_status_code=404,
                )

            documents_.append(document)
        return documents_


class SpecialChatParams(pydantic.BaseModel):
    user: str = pydantic.Field(default_factory=default_user)
    chat_name: str = pydantic.Field(
        default_factory=lambda: f"Chat {datetime.datetime.now():%x %X}"
    )


class Chat:
    """
    !!! tip

        This object is usually not instantiated manually, but rather through
        [ragna.core.Rag.chat][].

    Args:
        rag: The RAG workflow this chat is associated with.
        corpus: Corpus to use.
        assistant: Assistant to use.
        **params: Additional parameters passed to the source storage and assistant.
    """

    def __init__(
        self,
        rag: Rag,
        *,
        corpus: Corpus,
        assistant: Union[Type[Assistant], Assistant],
        **params: Any,
    ) -> None:
        self._rag = rag

        self.corpus = corpus
        self.assistant = self._rag._load_component(assistant)

        special_params = SpecialChatParams().model_dump()
        special_params.update(params)
        params = special_params
        self.params = params
        self._unpacked_params = self._unpack_chat_params(params)

        self._messages: list[Message] = []

    async def answer(self, prompt: str) -> Message:
        """Answer a prompt.

        Returns:
            Answer.
        """

        # TODO: Add welcome message if message list is empty

        prompt = Message(content=prompt, role=MessageRole.USER)
        self._messages.append(prompt)

        kwargs = self._unpacked_params[self.corpus.source_storage.retrieve]
        sources = await _run(
            self.corpus.source_storage.retrieve,
            self.corpus.documents,
            prompt.content,
            corpus_name=self.corpus.corpus_name,
            **kwargs,
        )
        kwargs = self._unpacked_params[self.assistant.answer]
        answer = Message(
            content=await _run(
                self.assistant.answer, prompt.content, sources, **kwargs
            ),
            role=MessageRole.ASSISTANT,
            sources=sources,
        )
        self._messages.append(answer)

        # FIXME: add error handling
        # return (
        #     "I'm sorry, but I'm having trouble helping you at this time. "
        #     "Please retry later. "
        #     "If this issue persists, please contact your administrator."
        # )

        return answer

    def _unpack_chat_params(
        self, params: dict[str, Any]
    ) -> dict[Callable, dict[str, Any]]:
        component_models = {
            getattr(component, name): model
            for component in [self.corpus.source_storage, self.assistant]
            for (_, name), model in component._protocol_models().items()
        }

        ChatModel = merge_models(
            str(self.params["chat_name"]),
            SpecialChatParams,
            *component_models.values(),
            config=pydantic.ConfigDict(extra="forbid"),
        )

        chat_params = ChatModel.model_validate(params, strict=True).model_dump(
            exclude_none=True
        )
        return {
            fn: model(**chat_params).model_dump()
            for fn, model in component_models.items()
        }

    # TODO: Do we need this?
    # async def __aenter__(self) -> Chat:
    #     await self.prepare()
    #     return self

    # async def __aexit__(
    #     self, exc_type: Type[Exception], exc: Exception, traceback: str
    # ) -> None:
    #     pass
