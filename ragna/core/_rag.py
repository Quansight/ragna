from __future__ import annotations

import asyncio
import datetime
import functools
import inspect
import uuid
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
import nest_asyncio
import pydantic

from ._components import Assistant, Component, Message, MessageRole, SourceStorage
from ._document import Document, LocalDocument
from ._utils import RagnaException, default_user, merge_models

T = TypeVar("T")
C = TypeVar("C", bound=Component)


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

    def chat(
        self,
        *,
        documents: Iterable[Any],
        source_storage: Union[Type[SourceStorage], SourceStorage],
        assistant: Union[Type[Assistant], Assistant],
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

    Prompts can be answered in a blocking

    ```python
    rag = Rag()

    with rag.chat(
        documents=[path],
        source_storage=ragna.core.RagnaDemoSourceStorage,
        assistant=ragna.core.RagnaDemoAssistant,
    ) as chat:
        print(chat("What is Ragna?"))
    ```

    or non-blocking manner

    ```python
    rag = Rag()

    async with rag.chat(
        documents=[path],
        source_storage=ragna.core.RagnaDemoSourceStorage,
        assistant=ragna.core.RagnaDemoAssistant,
    ) as chat:
        print(await chat.aanswer("What is Ragna?"))
    ```

    Args:
        rag: The RAG workflow this chat is associated with.
        documents: Documents to use. If any item is not a [ragna.core.Document][],
            [ragna.core.LocalDocument.from_path][] is invoked on it.
        source_storage: Source storage to use. If [str][] can be the
            [ragna.core.Component.display_name][] of any configured source storage.
        assistant: Assistant to use. If [str][] can be the
            [ragna.core.Component.display_name][] of any configured assistant.
        **params: Additional parameters passed to the source storage and assistant.
    """

    def __init__(
        self,
        rag: Rag,
        *,
        documents: Iterable[Any],
        source_storage: Union[Type[SourceStorage], SourceStorage],
        assistant: Union[Type[Assistant], Assistant],
        **params: Any,
    ) -> None:
        self._rag = rag

        self.documents = self._parse_documents(documents)
        self.source_storage = self._rag._load_component(source_storage)
        self.assistant = self._rag._load_component(assistant)

        special_params = SpecialChatParams().model_dump()
        special_params.update(params)
        params = special_params
        self.params = params
        self._unpacked_params = self._unpack_chat_params(params)

        self._prepared = False
        self._messages: list[Message] = []

    def prepare(self) -> Message:
        """Blocking variant of [ragna.core.Chat.aprepare][]

        Preparation can also be achieved through a context manager

        ```python
        with Rag().chat(...) as chat:
            answer = chat(...)
        ```
        """

        return self._run_async(self.aprepare())

    async def aprepare(self) -> Message:
        """Prepare the chat.

        This [`store`][ragna.core.SourceStorage.store]s the documents in the selected
        source storage. After preparation, prompts can be
        [answered][ragna.core.Chat.aanswer].

        Preparation can also be achieved through an async context manager

        ```python
        async with Rag().chat(...) as chat:
            answer = await chat.aanswer(...)
        ```

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

        await self._run(self.source_storage.store, self.documents)
        self._prepared = True

        welcome = Message(
            content="How can I help you with the documents?",
            role=MessageRole.SYSTEM,
        )
        self._messages.append(welcome)
        return welcome

    def answer(self, prompt: str) -> Message:
        """Blocking variant of [ragna.core.Chat.aanswer][]"""

        return self._run_async(self.aanswer(prompt))

    async def aanswer(self, prompt: str) -> Message:
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

        prompt = Message(content=prompt, role=MessageRole.USER)
        self._messages.append(prompt)

        sources = await self._run(
            self.source_storage.retrieve, self.documents, prompt.content
        )
        answer = Message(
            content=await self._run(self.assistant.answer, prompt.content, sources),
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

    def _run_async(self, fn: Awaitable[T]) -> T:
        # This is the best way I could come up with to be able to run an async function
        # synchronously when there is already an event-loop running. This happens for
        # example inside a jupyter notebook. Without this, it would be impossible to use
        # synchronous methods in such a scenario.
        # FIXME: That being said, it feels kinda hacky and is also causing issues in the
        #  test suite. If anyone knows a better way to achieve this, please send a PR :)
        nest_asyncio.apply()
        return asyncio.run(fn)  # type: ignore[arg-type]

    async def _run(self, fn: Callable[..., Union[T, Awaitable[T]]], *args: Any) -> T:
        kwargs = self._unpacked_params[fn]
        if inspect.iscoroutinefunction(fn):
            fn = cast(Callable[..., Awaitable[T]], fn)
            return await fn(*args, **kwargs)
        else:
            fn = cast(Callable[..., T], fn)
            return await anyio.to_thread.run_sync(
                functools.partial(fn, *args, **kwargs)
            )

    def __enter__(self) -> Chat:
        self.prepare()
        return self

    def __exit__(
        self, exc_type: Type[Exception], exc: Exception, traceback: str
    ) -> None:
        pass

    def __call__(self, prompt: str) -> Message:
        """Alias of [ragna.core.Chat.answer][]"""
        return self.answer(prompt)

    async def __aenter__(self) -> Chat:
        await self.aprepare()
        return self

    async def __aexit__(
        self, exc_type: Type[Exception], exc: Exception, traceback: str
    ) -> None:
        pass
