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
from ._source_storage import SourceStorage

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

        self._queue = Queue(self.config, load_components=load_components)

        self._chats: dict[(str, str), Chat] = {}

    async def new_chat(
        self,
        *,
        name: Optional[str] = None,
        documents: Sequence[Any],
        source_storage: Union[Type[RagComponent], RagComponent, str],
        assistant: Union[Type[RagComponent], RagComponent, str],
        **params,
    ):
        documents = self._parse_documents(documents)
        source_storage = self._queue.parse_component(source_storage, load=True)
        assistant = self._queue.parse_component(assistant, load=True)

        return Chat(
            queue=self._queue,
            name=name,
            documents=documents,
            source_storage=source_storage,
            assistant=assistant,
            **params,
        )

    def _parse_documents(self, documents: Sequence[Any]) -> list[Document]:
        documents_ = []
        for document in documents:
            if not isinstance(document, Document):
                document = self.config.document_class(document)

            if not document.is_available():
                raise RagnaException(
                    "Document not available",
                    document=document,
                    http_status_code=404,
                    http_detail=f"Document with ID {document.id} not available.",
                )

            documents_.append(document)
        return documents_


class Chat:
    def __init__(
        self,
        *,
        queue: Queue,
        name: Optional[str] = None,
        documents: list[Document],
        source_storage: Type[SourceStorage],
        assistant: Type[Assistant],
        messages: Optional[list[Message]] = None,
        **params: Any,
    ):
        self._queue = queue
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
        self._started = True

        welcome = Message(
            id=RagnaId.make(),
            content="How can I help you with the documents?",
            role=MessageRole.SYSTEM,
        )
        self.messages.append(welcome)

        return self

    async def close(self):
        self._closed = True
        return self

    async def answer(self, prompt: str):
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
        self.messages.append(prompt)

        sources = await self._enqueue(self.source_storage, "retrieve", prompt.content)
        content = await self._enqueue(self.assistant, "answer", prompt.content, sources)

        answer = Message(
            id=RagnaId.make(),
            content=content,
            role=MessageRole.ASSISTANT,
            sources=sources,
        )
        self.messages.append(answer)
        return answer

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
            return await self._queue.enqueue(
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
