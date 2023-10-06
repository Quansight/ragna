from __future__ import annotations

import datetime
import itertools
from collections import defaultdict
from typing import Any, Optional, Sequence, Type, TypeVar, Union

from pydantic import BaseModel, create_model, Extra

from ._assistant import Assistant, Message, MessageRole

from ._component import RagComponent
from ._config import Config
from ._core import RagnaException, RagnaId
from ._document import Document
from ._queue import Queue
from ._source_storage import ReconstructedSource, SourceStorage
from ._state import State

T = TypeVar("T", bound=RagComponent)


class Rag:
    def __init__(
        self,
        config: Optional[Config] = None,
        *,
        load_components: Optional[bool] = None,
    ):
        self.config = config or Config()
        self._logger = self.config.get_logger()

        self._state = State(self.config.state_database_url)
        self._queue = Queue(self.config, load_components=load_components)

        self._chats: dict[(str, str), Chat] = {}

    async def new_chat(
        self,
        *,
        user: str = "Ragna",
        name: Optional[str] = None,
        documents: Sequence[Any],
        source_storage: Union[Type[RagComponent], RagComponent, str],
        assistant: Union[Type[RagComponent], RagComponent, str],
        **params,
    ):
        """Create a new [ragna.core.Chat][] object from the given configuration."""
        documents = self._parse_documents(documents, user=user)
        source_storage = self._queue.load_component(source_storage)
        assistant = self._queue.load_component(assistant)

        chat = Chat(
            rag=self,
            user=user,
            id=RagnaId.make(),
            name=name,
            documents=documents,
            source_storage=source_storage,
            assistant=assistant,
            **params,
        )

        self._state.add_chat(
            id=chat.id,
            user=user,
            name=chat.name,
            document_ids=[document.id for document in documents],
            source_storage=source_storage.display_name(),
            assistant=assistant.display_name(),
            params=params,
        )

        return chat

    def _parse_documents(self, document: Sequence[Any], *, user: str) -> list[Document]:
        documents_ = []
        for document in document:
            if isinstance(document, RagnaId):
                document = self._get_document(id=document, user=user)
            else:
                if not isinstance(document, Document):
                    document = self.config.document_class(document)

                if document.id is None:
                    document.id = RagnaId.make()
                    self._add_document(
                        user=user,
                        id=document.id,
                        name=document.name,
                        metadata=document.metadata,
                    )

            if not document.is_available():
                raise RagnaException(
                    "Document not available",
                    document=document,
                    http_status_code=404,
                    http_detail=f"Document with ID {document.id} not available.",
                )

            documents_.append(document)
        return documents_

    def _add_document(self, *, user: str, id: RagnaId, name: str, metadata):
        self._state.add_document(user=user, id=id, name=name, metadata=metadata)

    def _get_document(self, user: str, id: RagnaId):
        state = self._state.get_document(user=user, id=id)
        if state is None:
            raise RagnaException(
                "Document not found",
                user=user,
                id=id,
                http_status_code=404,
                http_detail=RagnaException.EVENT,
            )
        return self.config.document_class(
            id=id, name=state.name, metadata=state.metadata_
        )

    def _get_chats(self, *, user: str):
        chats = [
            Chat(
                rag=self,
                user=user,
                id=chat_state.id,
                name=chat_state.name,
                documents=[
                    self.config.document_class(
                        id=document_state.id,
                        name=document_state.name,
                        metadata=document_state.metadata_,
                    )
                    for document_state in chat_state.document_states
                ],
                source_storage=self._queue.load_component(chat_state.source_storage),
                assistant=self._queue.load_component(chat_state.assistant),
                messages=[
                    Message(
                        id=message_state.id,
                        content=message_state.content,
                        role=message_state.role,
                        sources=[
                            ReconstructedSource(
                                id=source_state.id,
                                document_id=source_state.document_id,
                                document_name=source_state.document_state.name,
                                location=source_state.location,
                            )
                            for source_state in message_state.source_states
                        ],
                    )
                    for message_state in chat_state.message_states
                ],
                **chat_state.params,
            )
            for chat_state in self._state.get_chats(user=user)
        ]
        self._chats.update({(user, chat.id): chat for chat in chats})
        return chats

    def _get_chat(self, *, user: str, id: RagnaId):
        key = (user, id)

        chat = self._chats.get(key)
        if chat is not None:
            return chat

        self._get_chats(user=user)

        chat = self._chats.get(key)
        if chat is not None:
            return chat

        raise RagnaException(
            "Chat not found",
            user=user,
            id=id,
            http_status_code=404,
            detail=RagnaException.EVENT,
        )


class Chat:
    """
    !!! note

        This object is usually not instantiated manually, but rather through
        [ragna.core.Rag.new_chat][].

    A chat needs to be [`start`][ragna.core.Chat.start]ed before prompts can be
    [`answer`][ragna.core.Chat.answer]ed. Optionally, it can be
    [`close`][ragna.core.Chat.close]d to no longer accept new prompts.

    Can be used as context manager to automatically invoke
    [`start`][ragna.core.Chat.start] and [`close`][ragna.core.Chat.close]:

    ```python
    rag = Rag()

    async with await rag.new_chat(
        documents=[path],
        source_storage=ragna.core.RagnaDemoSourceStorage,
        assistant=ragna.core.RagnaDemoAssistant,
    ) as chat:
        print(await chat.answer("What is Ragna?"))
    ```
    """

    def __init__(
        self,
        *,
        rag: Rag,
        user: str,
        id: RagnaId,
        name: Optional[str] = None,
        documents,
        source_storage: Type[SourceStorage],
        assistant: Type[Assistant],
        messages: Optional[list[Message]] = None,
        **params,
    ):
        self._rag = rag
        self._state = self._rag._state
        self._user = user

        self.id = id
        self.name = name or f"{datetime.datetime.now():%c}"
        self.documents = documents
        self.source_storage = source_storage
        self.assistant = assistant

        self.params = params
        self._unpacked_params = self._unpack_chat_params(params)

        self.messages = messages or []

        self._started = False
        self._closed = False

    async def start(self):
        """Start the chat.

        This [`store`][ragna.core.SourceStorage.store]s the documents in the selected
        source storage.

        Raises:
            ragna.core.RagnaException: If chat is already
                [`start`][ragna.core.Chat.start]'ed.
            ragna.core.RagnaException: If chat is [`close`][ragna.core.Chat.close]'ed.
        """
        if self._started:
            raise RagnaException(
                "Chat is already started",
                chat=self,
                http_status_code=400,
                detail=RagnaException.EVENT,
            )
        elif self._closed:
            raise RagnaException(
                "Chat is closed and cannot be restarted",
                chat=self,
                http_status_code=400,
                http_detail=RagnaException.EVENT,
            )

        await self._enqueue(self.source_storage, "store", self.documents)
        self._state.start_chat(user=self._user, id=self.id)
        self._started = True

        welcome = Message(
            id=RagnaId.make(),
            content="How can I help you with the documents?",
            role=MessageRole.SYSTEM,
        )
        self._append_message(welcome)

        return self

    async def close(self):
        """Close that chat.

        After the chat is closed, new prompts will no longer be
        [`answer`][ragna.core.Chat.answer]'ed.
        """
        self._state.close_chat(id=self.id, user=self._user)
        self._closed = True

        return self

    async def answer(self, prompt: str):
        """Answer a prompt

        Raises:
            ragna.core.RagnaException: If chat is not
                [`start`][ragna.core.Chat.start]'ed.
            ragna.core.RagnaException: If chat is [`close`][ragna.core.Chat.close]'ed.
        """

        if not self._started:
            raise RagnaException(
                "Chat is not started",
                chat=self,
                http_status_code=400,
                detail=RagnaException.EVENT,
            )
        elif self._closed:
            raise RagnaException(
                "Chat is closed",
                chat=self,
                http_status_code=400,
                http_detail=RagnaException.EVENT,
            )

        prompt = Message(id=RagnaId.make(), content=prompt, role=MessageRole.USER)
        self._append_message(prompt)

        sources = await self._enqueue(self.source_storage, "retrieve", prompt.content)
        content = await self._enqueue(self.assistant, "answer", prompt.content, sources)

        answer = Message(
            id=RagnaId.make(),
            content=content,
            role=MessageRole.ASSISTANT,
            sources=sources,
        )
        self._append_message(answer)
        return answer

    def _append_message(self, message: Message):
        self.messages.append(message)
        self._state.add_message(
            message,
            user=self._user,
            chat_id=self.id,
        )

    class _SpecialChatParams(BaseModel):
        user: str
        chat_id: RagnaId
        chat_name: str

    def _unpack_chat_params(self, params):
        source_storage_models = self.source_storage._models()
        assistant_models = self.assistant._models()

        ChatModel = self._merge_models(
            self._SpecialChatParams,
            *source_storage_models.values(),
            *assistant_models.values(),
        )

        chat_model = ChatModel(
            user=self._user,
            chat_id=self.id,
            chat_name=self.name,
            **params,
        )
        chat_params = chat_model.dict(exclude_none=True)
        return {
            component_and_action: model(**chat_params).dict()
            for component_and_action, model in itertools.chain(
                source_storage_models.items(), assistant_models.items()
            )
        }

    def _merge_models(self, *models):
        raw_field_definitions = defaultdict(list)
        for model_cls in models:
            for name, field in model_cls.__fields__.items():
                raw_field_definitions[name].append(
                    (field.type_, ... if field.required else field.default)
                )

        field_definitions = {}
        for name, definitions in raw_field_definitions.items():
            if len(definitions) == 1:
                field_definitions[name] = definitions[0]
                continue

            types, defaults = zip(*definitions)

            types = set(types)
            if len(types) > 1:
                raise RagnaException(f"Mismatching types for field {name}: {types}")
            type_ = types.pop()

            default = ... if any(default is ... for default in defaults) else None

            field_definitions[name] = (type_, default)

        class Config:
            extra = Extra.forbid

        return create_model(str(self), __config__=Config, **field_definitions)

    async def _enqueue(self, component, action, *args):
        try:
            return await self._rag._queue.enqueue(
                component, action, args, self._unpacked_params[(component, action)]
            )
        except RagnaException as exc:
            exc.extra["component"] = component.display_name()
            exc.extra["action"] = action
            raise exc

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *_):
        await self.close()
