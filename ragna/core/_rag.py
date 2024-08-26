from __future__ import annotations

import contextlib
import datetime
import inspect
import itertools
import uuid
from collections import defaultdict
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
import pydantic_core
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from ._components import Assistant, Component, Message, MessageRole, SourceStorage
from ._document import Document, LocalDocument
from ._utils import RagnaException, default_user, merge_models

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
        **params: Any,
    ) -> None:
        self._rag = rag

        self.documents = self._parse_documents(documents)
        self.source_storage = cast(
            SourceStorage, self._rag._load_component(source_storage)
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

        await self._run(self.source_storage.store, self.documents)
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

        sources = await self._run(self.source_storage.retrieve, self.documents, prompt)

        question = Message(content=prompt, role=MessageRole.USER, sources=sources)
        self._messages.append(question)

        answer = Message(
            content=self._run_gen(self.assistant.answer, self._messages.copy()),
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
        # This method does two things:
        # 1. Validate the **params against the signatures of the protocol methods of the
        #    used components. This makes sure that
        #    - No parameter is passed that isn't used by at least one component
        #    - No parameter is missing that is needed by at least one component
        #    - No parameter is passed in the wrong type
        # 2. Prepare the distribution of the parameters to the protocol method that
        #    requested them. The actual distribution happens in self._run and
        #    self._run_gen, but is only a dictionary lookup by then.
        component_models = {
            getattr(component, name): model
            for component in [self.source_storage, self.assistant]
            for (_, name), model in component._protocol_models().items()
        }

        ChatModel = merge_models(
            f"{self.__module__}.{type(self).__name__}-{self.params['chat_id']}",
            SpecialChatParams,
            *component_models.values(),
            config=pydantic.ConfigDict(extra="forbid"),
        )

        with self._format_validation_error(ChatModel):
            chat_model = ChatModel.model_validate(params, strict=True)

        chat_params = chat_model.model_dump(exclude_none=True)
        return {
            fn: model(**chat_params).model_dump()
            for fn, model in component_models.items()
        }

    @contextlib.contextmanager
    def _format_validation_error(
        self, model_cls: type[pydantic.BaseModel]
    ) -> Iterator[None]:
        try:
            yield
        except pydantic.ValidationError as validation_error:
            errors = defaultdict(list)
            for error in validation_error.errors():
                errors[error["type"]].append(error)

            parts = [
                f"Validating the Chat parameters resulted in {validation_error.error_count()} errors:",
                "",
            ]

            def format_error(
                error: pydantic_core.ErrorDetails,
                *,
                annotation: bool = False,
                value: bool = False,
            ) -> str:
                param = cast(str, error["loc"][0])

                formatted_error = f"- {param}"
                if annotation:
                    annotation_ = cast(
                        type, model_cls.model_fields[param].annotation
                    ).__name__
                    formatted_error += f": {annotation_}"

                if value:
                    value_ = error["input"]
                    formatted_error += (
                        f" = {value_!r}" if annotation else f"={value_!r}"
                    )

                return formatted_error

            if "extra_forbidden" in errors:
                parts.extend(
                    [
                        "The following parameters are unknown:",
                        "",
                        *[
                            format_error(error, value=True)
                            for error in errors["extra_forbidden"]
                        ],
                        "",
                    ]
                )

            if "missing" in errors:
                parts.extend(
                    [
                        "The following parameters are missing:",
                        "",
                        *[
                            format_error(error, annotation=True)
                            for error in errors["missing"]
                        ],
                        "",
                    ]
                )

            type_errors = ["string_type", "int_type", "float_type", "bool_type"]
            if any(type_error in errors for type_error in type_errors):
                parts.extend(
                    [
                        "The following parameters have the wrong type:",
                        "",
                        *[
                            format_error(error, annotation=True, value=True)
                            for error in itertools.chain.from_iterable(
                                errors[type_error] for type_error in type_errors
                            )
                        ],
                        "",
                    ]
                )

            raise RagnaException("\n".join(parts))

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
