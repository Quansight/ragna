from __future__ import annotations

import collections.abc
import contextlib
import datetime
import itertools
import uuid
from collections import defaultdict
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Collection,
    Generic,
    Iterator,
    Optional,
    TypeVar,
    Union,
    cast,
)

import pydantic
import pydantic_core
from fastapi import status

from ragna._utils import as_async_iterator, as_awaitable, default_user

from ._components import Assistant, Component, Message, MessageRole, SourceStorage
from ._document import Document, LocalDocument
from ._metadata_filter import MetadataFilter
from ._utils import RagnaException, merge_models

if TYPE_CHECKING:
    from ragna.deploy import Config

T = TypeVar("T")
C = TypeVar("C", bound=Component, covariant=True)


class Rag(Generic[C]):
    """RAG workflow.

    !!! tip

        This class can be imported from `ragna` directly, e.g.

        ```python
        from ragna import Rag
        ```
    """

    def __init__(
        self,
        *,
        config: Optional[Config] = None,
        ignore_unavailable_components: bool = False,
    ) -> None:
        self._components: dict[type[C], C] = {}
        self._display_name_map: dict[str, type[C]] = {}

        if config is not None:
            self._preload_components(
                config=config,
                ignore_unavailable_components=ignore_unavailable_components,
            )

    def _preload_components(
        self, *, config: Config, ignore_unavailable_components: bool
    ) -> None:
        for components in [config.source_storages, config.assistants]:
            components = cast(list[type[Component]], components)
            at_least_one = False
            for component in components:
                loaded_component = self._load_component(
                    component,  #  type: ignore[arg-type]
                    ignore_unavailable=ignore_unavailable_components,
                )
                if loaded_component is None:
                    print(
                        f"Ignoring {component.display_name()}, because it is not available."
                    )
                else:
                    at_least_one = True

            if not at_least_one:
                raise RagnaException(
                    "No component available",
                    components=[component.display_name() for component in components],
                )

    def _load_component(
        self, component: Union[C, type[C], str], *, ignore_unavailable: bool = False
    ) -> Optional[C]:
        cls: type[C]
        instance: Optional[C]

        if isinstance(component, Component):
            instance = cast(C, component)
            cls = type(instance)
        elif isinstance(component, type) and issubclass(component, Component):
            cls = component
            instance = None
        elif isinstance(component, str):
            try:
                cls = self._display_name_map[component]
            except KeyError:
                raise RagnaException(
                    "Unknown component",
                    display_name=component,
                    help="Did you forget to create the Rag() instance with a config?",
                    http_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    http_detail=f"Unknown component '{component}'",
                ) from None

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
            self._display_name_map[cls.display_name()] = cls

        return self._components[cls]

    def chat(
        self,
        input: Union[
            None,
            MetadataFilter,
            Document,
            str,
            Path,
            Collection[Union[Document, str, Path]],
        ] = None,
        *,
        source_storage: Union[SourceStorage, type[SourceStorage], str],
        assistant: Union[Assistant, type[Assistant], str],
        corpus_name: str = "default",
        **params: Any,
    ) -> Chat:
        """Create a new [ragna.core.Chat][].

        Args:
            input: Subject of the chat. Available options:

                - `None`: Use the full corpus of documents specified by `corpus_name`.
                -  [ragna.core.MetadataFilter][]: Use the given subset of the corpus of
                   documents specified by `corpus_name`.
                - Single document or a collection of documents to use. If any item is
                  not a [ragna.core.Document][], it is assumed to be a path and
                  [ragna.core.LocalDocument.from_path][] is invoked on it.
                source_storage: Source storage to use.
            assistant: Assistant to use.
            corpus_name: Corpus of documents to use.
            **params: Additional parameters passed to the source storage and assistant.
        """
        return Chat(
            self,
            input=input,
            source_storage=cast(SourceStorage, self._load_component(source_storage)),  # type: ignore[arg-type]
            assistant=cast(Assistant, self._load_component(assistant)),  # type: ignore[arg-type]
            corpus_name=corpus_name,
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
        input: Subject of the chat. Available options:

            - `None`: Use the full corpus of documents specified by `corpus_name`.
            -  [ragna.core.MetadataFilter][]: Use the given subset of the corpus of
               documents specified by `corpus_name`.
            - Single document or a collection of documents to use. If any item is
              not a [ragna.core.Document][], it is assumed to be a path and
              [ragna.core.LocalDocument.from_path][] is invoked on it.
        source_storage: Source storage to use.
        assistant: Assistant to use.
        corpus_name: Corpus of documents to use.
        **params: Additional parameters passed to the source storage and assistant.
    """

    def __init__(
        self,
        rag: Rag,
        input: Union[
            None,
            MetadataFilter,
            Document,
            str,
            Path,
            Collection[Union[Document, str, Path]],
        ] = None,
        *,
        source_storage: SourceStorage,
        assistant: Assistant,
        corpus_name: str = "default",
        **params: Any,
    ) -> None:
        self._rag = rag

        self.documents, self.metadata_filter, self._prepared = self._parse_input(input)
        self.source_storage = source_storage
        self.assistant = assistant
        self.corpus_name = corpus_name

        special_params = SpecialChatParams().model_dump()
        special_params.update(params)
        params = special_params
        self.params = params
        self._unpacked_params = self._unpack_chat_params(params)

        self._messages: list[Message] = []

    async def prepare(self) -> Message:
        """Prepare the chat.

        This [`store`][ragna.core.SourceStorage.store]s the documents in the selected
        source storage. Afterwards prompts can be [`answer`][ragna.core.Chat.answer]ed.

        Returns:
            Welcome message.
        """
        welcome = Message(
            content="How can I help you with the documents?",
            role=MessageRole.SYSTEM,
        )

        if self._prepared:
            return welcome

        await self._as_awaitable(
            self.source_storage.store, self.corpus_name, self.documents
        )
        self._prepared = True

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
                http_status_code=status.HTTP_400_BAD_REQUEST,
                http_detail=RagnaException.EVENT,
            )

        sources = await self._as_awaitable(
            self.source_storage.retrieve, self.corpus_name, self.metadata_filter, prompt
        )
        if not sources:
            event = "Unable to retrieve any sources."
            if not self.documents and self.metadata_filter is None:
                suggestion = "Did you forget to pass document(s) to the chat?"
            elif self.metadata_filter:
                suggestion = "Is your metadata_filter too strict?"
            else:
                suggestion = None

            if suggestion is not None:
                event = f"{event} {suggestion}"

            raise RagnaException(
                event,
                http_status_code=status.HTTP_400_BAD_REQUEST,
                http_detail=RagnaException.EVENT,
            )

        question = Message(content=prompt, role=MessageRole.USER, sources=sources)
        self._messages.append(question)

        answer = Message(
            content=self._as_async_iterator(
                self.assistant.answer, self._messages.copy()
            ),
            role=MessageRole.ASSISTANT,
            sources=sources,
        )
        if not stream:
            await answer.read()

        self._messages.append(answer)

        return answer

    def _parse_input(
        self,
        input: Union[
            MetadataFilter,
            None,
            Document,
            str,
            Path,
            Collection[Union[Document, str, Path]],
        ],
    ) -> tuple[Optional[list[Document]], Optional[MetadataFilter], bool]:
        if isinstance(input, MetadataFilter) or input is None:
            return None, input, True

        if isinstance(input, str) or not isinstance(input, collections.abc.Collection):
            input = [input]

        documents = [
            (
                document
                if isinstance(document, Document)
                else LocalDocument.from_path(document)
            )
            for document in input
        ]

        metadata_filter = MetadataFilter.or_(
            [
                MetadataFilter.eq("document_id", str(document.id))
                for document in documents
            ]
        )
        return documents, metadata_filter, False

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
                        type, model_cls.__pydantic_fields__[param].annotation
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

    def _as_awaitable(
        self, fn: Union[Callable[..., T], Callable[..., Awaitable[T]]], *args: Any
    ) -> Awaitable[T]:
        return as_awaitable(fn, *args, **self._unpacked_params[fn])

    def _as_async_iterator(
        self,
        fn: Union[Callable[..., Iterator[T]], Callable[..., AsyncIterator[T]]],
        *args: Any,
    ) -> AsyncIterator[T]:
        return as_async_iterator(fn, *args, **self._unpacked_params[fn])

    async def __aenter__(self) -> Chat:
        await self.prepare()
        return self

    async def __aexit__(
        self, exc_type: type[Exception], exc: Exception, traceback: str
    ) -> None:
        pass
