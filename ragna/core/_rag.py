from __future__ import annotations

import datetime

import itertools
import os
import uuid
from collections import defaultdict
from typing import Any, Iterable, Optional, Type, Union

from pydantic import BaseModel, create_model, Extra, Field

from ._assistant import Assistant, Message, MessageRole

from ._config import Config
from ._core import RagnaException
from ._document import Document
from ._queue import Queue
from ._source_storage import SourceStorage


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

    def chat(
        self,
        documents: Iterable[Any],
        source_storage: Union[Type[SourceStorage], SourceStorage, str],
        assistant: Union[Type[Assistant], Assistant, str],
        **params: Any,
    ):
        return Chat(
            self,
            documents=documents,
            source_storage=source_storage,
            assistant=assistant,
            **params,
        )


class Chat:
    def __init__(
        self,
        rag: Rag,
        *,
        documents: Iterable[Any],
        source_storage: Union[Type[SourceStorage], SourceStorage, str],
        assistant: Union[Type[Assistant], Assistant, str],
        **params: Any,
    ):
        self._rag = rag

        self.documents = self._parse_documents(documents)
        # FIXME: doesn't this load on the main thread???
        self.source_storage = self._rag._queue.parse_component(
            source_storage, load=True
        )
        self.assistant = self._rag._queue.parse_component(assistant, load=True)

        special_params = self._SpecialChatParams().dict()
        special_params.update(params)
        params = special_params
        self.params = params
        self._unpacked_params = self._unpack_chat_params(params)

        self._prepared = False
        self._messages = []

    async def prepare(self):
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

    async def answer(self, prompt: str):
        if not self._prepared:
            raise RagnaException(
                "Chat is not prepared",
                chat=self,
                http_status_code=400,
                detail=RagnaException.EVENT,
            )

        prompt = Message(content=prompt, role=MessageRole.USER)
        self._messages.append(prompt)

        sources = await self._enqueue(self.source_storage, "retrieve", prompt.content)
        content = await self._enqueue(self.assistant, "answer", prompt.content, sources)

        answer = Message(
            content=content,
            role=MessageRole.ASSISTANT,
            sources=sources,
        )
        self._messages.append(answer)
        return answer

    def _parse_documents(self, documents: Iterable[Any]) -> list[Document]:
        documents_ = []
        for document in documents:
            if not isinstance(document, Document):
                document = self._rag.config.document_class(document)

            if not document.is_available():
                raise RagnaException(
                    "Document not available",
                    document=document,
                    http_status_code=404,
                )

            documents_.append(document)
        return documents_

    class _SpecialChatParams(BaseModel):
        user: str = Field(default_factory=os.getlogin)
        chat_id: uuid.UUID = Field(default_factory=uuid.uuid4)
        chat_name: str = Field(
            default_factory=lambda: f"Chat {datetime.datetime.now():%x %X}"
        )

    def _unpack_chat_params(self, params):
        source_storage_models = self.source_storage._models()
        assistant_models = self.assistant._models()

        ChatModel = self._merge_models(
            self._SpecialChatParams,
            *source_storage_models.values(),
            *assistant_models.values(),
        )

        chat_params = ChatModel(**params).dict(exclude_none=True)
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
                raw_field_definitions[name].append((field.type_, field.required))

        field_definitions = {}
        for name, definitions in raw_field_definitions.items():
            types, requireds = zip(*definitions)

            types = set(types)
            if len(types) > 1:
                raise RagnaException(f"Mismatching types for field {name}: {types}")
            type_ = types.pop()

            default = ... if any(requireds) else None

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
        await self.prepare()
        return self

    async def __aexit__(self, *exc_info):
        pass
