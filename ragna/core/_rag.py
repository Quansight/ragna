from __future__ import annotations

import datetime
import itertools
import uuid
from typing import Any, Iterable, Optional, Type, TypeVar, Union

import pydantic

from ._components import Assistant, Component, Message, MessageRole, SourceStorage
from ._config import Config
from ._document import Document
from ._queue import Queue
from ._utils import RagnaException, default_user, merge_models

T = TypeVar("T", bound=Component)


class Rag:
    """RAG workflow.

    Args:
        config: Ragna configuration.
        load_components: Whether to load the configured components in the current
            process. If omitted, components will be loaded if a memory queue is
            configured.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        *,
        load_components: Optional[bool] = None,
    ):
        self.config = config or Config()
        self._queue = Queue(self.config, load_components=load_components)

    def chat(
        self,
        *,
        documents: Iterable[Any],
        source_storage: Union[Type[SourceStorage], SourceStorage, str],
        assistant: Union[Type[Assistant], Assistant, str],
        **params: Any,
    ) -> Chat:
        """Create a new [ragna.core.Chat][].

        Args:
            documents: Documents to use. Items that are not [ragna.core.Document][]s are
                passed as positional argument to the configured document class.

                !!! note

                    The default configuration uses [ragna.core.LocalDocument][] as
                    document class. It accepts a path as positional input to create it.
                    Thus, in this configuration you can pass paths as documents.
            source_storage: Source storage to use. If [str][] can be the
                [ragna.core.Component.display_name][] of any configured source
                storage.
            assistant: Assistant to use. If [str][] can be the
                [ragna.core.Component.display_name][] of any configured assistant.
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
        documents: Documents to use. Items that are not [ragna.core.Document][]s are
            passed as positional argument to the configured document class.

            !!! note

                The default configuration uses [ragna.core.LocalDocument][] as document
                class. It accepts a path as positional input to create it. Thus, in
                this configuration you can pass paths as documents.
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
        source_storage: Union[Type[SourceStorage], SourceStorage, str],
        assistant: Union[Type[Assistant], Assistant, str],
        **params: Any,
    ) -> None:
        self._rag = rag

        self.documents = self._parse_documents(documents)
        self.source_storage = self._rag._queue.parse_component(source_storage)
        self.assistant = self._rag._queue.parse_component(assistant)

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

        await self._enqueue(self.source_storage, "store", self.documents)
        self._prepared = True

        welcome = Message(
            content="How can I help you with the documents?",
            role=MessageRole.SYSTEM,
        )
        self._messages.append(welcome)
        return welcome

    async def answer(self, prompt: str) -> Message:
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

        sources = await self._enqueue(
            self.source_storage, "retrieve", self.documents, prompt.content
        )
        answer = Message(
            content=await self._enqueue(
                self.assistant, "answer", prompt.content, sources
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

    def _parse_documents(self, documents: Iterable[Any]) -> list[Document]:
        documents_ = []
        for document in documents:
            if not isinstance(document, Document):
                document = self._rag.config.core.document(
                    document  # type: ignore[misc, call-arg]
                )

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
    ) -> dict[tuple[Type[Component], str], dict[str, Any]]:
        source_storage_models = self.source_storage._protocol_models()
        assistant_models = self.assistant._protocol_models()

        ChatModel = merge_models(
            str(self.params["chat_id"]),
            SpecialChatParams,
            *source_storage_models.values(),
            *assistant_models.values(),
            config=pydantic.ConfigDict(extra="forbid"),
        )

        chat_params = ChatModel.model_validate(params, strict=True).model_dump(
            exclude_none=True
        )
        return {
            component_and_action: model(**chat_params).model_dump()
            for component_and_action, model in itertools.chain(
                source_storage_models.items(), assistant_models.items()
            )
        }

    async def _enqueue(
        self, component: Type[Component], action: str, *args: Any
    ) -> Any:
        try:
            return await self._rag._queue.enqueue(
                component, action, args, self._unpacked_params[(component, action)]
            )
        except RagnaException as exc:
            exc.extra["component"] = component.display_name()
            exc.extra["action"] = action
            raise exc

    async def __aenter__(self) -> Chat:
        await self.prepare()
        return self

    async def __aexit__(
        self, exc_type: Type[Exception], exc: Exception, traceback: str
    ) -> None:
        pass
