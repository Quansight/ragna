from __future__ import annotations

import datetime
import inspect
import uuid
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Iterator,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

import pydantic
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from ._components import Assistant, Component, Embedding, Message, MessageRole, SourceStorage
from ._document import Document, LocalDocument
from ._utils import RagnaException, default_user, merge_models

from ragna.embedding_models._embedding import EmbeddingModel
from ragna.source_storages._vector_database import VectorDatabaseSourceStorage

T = TypeVar("T")
C = TypeVar("C", bound=Component)


class Rag(Generic[C]):
    """RAG workflow.

    !!! tip

        This class can be imported from `ragna` directly, e.g.

        ```python
        from ragna import Rag
        ```
    """

    def __init__(self) -> None:
        self._components: dict[Type[C], C] = {}

    def _load_component(
        self, component: Union[Type[C], C], *, ignore_unavailable: bool = False
    ) -> Optional[C]:
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
                    if ignore_unavailable:
                        return None

                    raise RagnaException(
                        "Component not available", name=cls.display_name()
                    )
                instance = cls()

            self._components[cls] = instance

        return self._components[cls]

    def chat(
        self,
        *,
        documents: Iterable[Any],
        source_storage: Union[Type[SourceStorage], SourceStorage],
        assistant: Union[Type[Assistant], Assistant],
        embedding_model: Optional[Union[Type[EmbeddingModel], EmbeddingModel]] = None,
        **params: Any,
    ) -> Chat:
        """Create a new [ragna.core.Chat][].

        Args:
            documents: Documents to use. If any item is not a [ragna.core.Document][],
                [ragna.core.LocalDocument.from_path][] is invoked on it.
            source_storage: Source storage to use.
            assistant: Assistant to use.
            **params: Additional parameters passed to the source storage and assistant.
        """
        return Chat(
            self,
            documents=documents,
            source_storage=source_storage,
            assistant=assistant,
            embedding_model=embedding_model,
            **params,
        )


class SpecialChatParams(pydantic.BaseModel):
    user: str = pydantic.Field(default_factory=default_user)
    chat_id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    chat_name: str = pydantic.Field(
        default_factory=lambda: f"Chat {datetime.datetime.now():%x %X}"
    )


class Chat:
    """
    !!! tip

        This object is usually not instantiated manually, but rather through
        [ragna.core.Rag.chat][].

    A chat needs to be [`prepare`][ragna.core.Chat.prepare]d before prompts can be
    [`answer`][ragna.core.Chat.answer]ed.

    Can be used as context manager to automatically invoke
    [`prepare`][ragna.core.Chat.prepare]:

    ```python
    rag = Rag()

    async with rag.chat(
        documents=[path],
        source_storage=ragna.core.RagnaDemoSourceStorage,
        assistant=ragna.core.RagnaDemoAssistant,
    ) as chat:
        print(await chat.answer("What is Ragna?"))
    ```

    Args:
        rag: The RAG workflow this chat is associated with.
        documents: Documents to use. If any item is not a [ragna.core.Document][],
            [ragna.core.LocalDocument.from_path][] is invoked on it.
        source_storage: Source storage to use.
        assistant: Assistant to use.
        **params: Additional parameters passed to the source storage and assistant.
    """

    def __init__(
        self,
        rag: Rag,
        *,
        documents: Iterable[Any],
        source_storage: Union[Type[SourceStorage], SourceStorage],
        assistant: Union[Type[Assistant], Assistant],
        embedding_model: Union[Type[EmbeddingModel], EmbeddingModel],
        **params: Any,
    ) -> None:
        self._rag = rag

        if embedding_model is None and issubclass(source_storage.__ragna_input_type__, Embedding):
            raise RagnaException

        self.embedding_model = cast(EmbeddingModel, self._rag._load_component(embedding_model))

        self.documents = self._parse_documents(documents)
        self.source_storage = cast(
            VectorDatabaseSourceStorage, self._rag._load_component(source_storage)
        )
        self.assistant = cast(Assistant, self._rag._load_component(assistant))

        special_params = SpecialChatParams().model_dump()
        special_params.update(params)
        params = special_params
        self.params = params
        self._unpacked_params = self._unpack_chat_params(params)

        self._prepared = False
        self._messages: list[Message] = []

    async def prepare(self) -> Message:
        """Prepare the chat.

        This [`store`][ragna.core.SourceStorage.store]s the documents in the selected
        source storage. Afterwards prompts can be [`answer`][ragna.core.Chat.answer]ed.

        Returns:
            Welcome message.

        Raises:
            ragna.core.RagnaException: If chat is already
                [`prepare`][ragna.core.Chat.prepare]d.
        """
        if self._prepared:
            raise RagnaException(
                "Chat is already prepared",
                chat=self,
                http_status_code=400,
                detail=RagnaException.EVENT,
            )

        from ragna.core import Document
        if issubclass(self.source_storage.__ragna_input_type__, Document):
            await self._run(self.source_storage.store, self.documents)
        else:
            # Here we need to generate the list of embeddings
            chunks = []
            for document in self.documents:
                chunks += self.embedding_model._chunk_pages(document.extract_pages(), document_id=document.id, chunk_size=500, chunk_overlap=250)
            embeddings = self.embedding_model.embed_chunks(chunks)
            await self._run(self.source_storage.store, embeddings)

        self._prepared = True

        welcome = Message(
            content="How can I help you with the documents?",
            role=MessageRole.SYSTEM,
        )
        self._messages.append(welcome)
        return welcome

    async def answer(self, prompt: str, *, stream: bool = False) -> Message:
        """Answer a prompt.

        Returns:
            Answer.

        Raises:
            ragna.core.RagnaException: If chat is not
                [`prepare`][ragna.core.Chat.prepare]d.
        """
        if not self._prepared:
            raise RagnaException(
                "Chat is not prepared",
                chat=self,
                http_status_code=400,
                detail=RagnaException.EVENT,
            )

        self._messages.append(Message(content=prompt, role=MessageRole.USER))

        if issubclass(self.source_storage.__ragna_input_type__, Document):
            sources = await self._run(self.source_storage.retrieve, self.documents, prompt)
        else:
            sources = await self._run(self.source_storage.retrieve, self.documents,
                                      self.embedding_model.embed_text(prompt))

        answer = Message(
            content=self._run_gen(self.assistant.answer, prompt, sources),
            role=MessageRole.ASSISTANT,
            sources=sources,
        )
        if not stream:
            await answer.read()

        self._messages.append(answer)

        return answer

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

    def _unpack_chat_params(
        self, params: dict[str, Any]
    ) -> dict[Callable, dict[str, Any]]:
        component_models = {
            getattr(component, name): model
            for component in [self.source_storage, self.assistant]
            for (_, name), model in component._protocol_models().items()
        }

        ChatModel = merge_models(
            str(self.params["chat_id"]),
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

    async def _run(
        self, fn: Union[Callable[..., T], Callable[..., Awaitable[T]]], *args: Any
    ) -> T:
        kwargs = self._unpacked_params[fn]
        if inspect.iscoroutinefunction(fn):
            fn = cast(Callable[..., Awaitable[T]], fn)
            coro = fn(*args, **kwargs)
        else:
            fn = cast(Callable[..., T], fn)
            coro = run_in_threadpool(fn, *args, **kwargs)

        return await coro

    async def _run_gen(
        self,
        fn: Union[Callable[..., Iterator[T]], Callable[..., AsyncIterator[T]]],
        *args: Any,
    ) -> AsyncIterator[T]:
        kwargs = self._unpacked_params[fn]
        if inspect.isasyncgenfunction(fn):
            fn = cast(Callable[..., AsyncIterator[T]], fn)
            async_gen = fn(*args, **kwargs)
        else:
            fn = cast(Callable[..., Iterator[T]], fn)
            async_gen = iterate_in_threadpool(fn(*args, **kwargs))

        async for item in async_gen:
            yield item

    async def __aenter__(self) -> Chat:
        await self.prepare()
        return self

    async def __aexit__(
        self, exc_type: Type[Exception], exc: Exception, traceback: str
    ) -> None:
        pass
