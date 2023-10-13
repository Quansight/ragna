from __future__ import annotations

import datetime
import itertools
import os
import uuid
from collections import defaultdict
from typing import Any, Iterable, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ConfigDict, create_model, Extra, Field

from ._components import Assistant, Component, Message, MessageRole, SourceStorage

from ._config import Config
from ._document import Document
from ._queue import Queue
from ._utils import RagnaException

T = TypeVar("T", bound=Component)


class Rag:
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
    ):
        """Create a new [ragna.core.Chat][]."""
        return Chat(
            self,
            documents=documents,
            source_storage=source_storage,
            assistant=assistant,
            **params,
        )


class Chat:
    """
    !!! note

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
    """

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
        self.source_storage = self._rag._queue.parse_component(source_storage)
        self.assistant = self._rag._queue.parse_component(assistant)

        special_params = self._SpecialChatParams().model_dump()
        special_params.update(params)
        params = special_params
        self.params = params
        self._unpacked_params = self._unpack_chat_params(params)

        self._prepared = False
        self._messages = []

    async def prepare(self):
        """Prepare the chat.

        This [`store`][ragna.core.SourceStorage.store]s the documents in the selected
        source storage. Afterwards prompts can be [`answer`][ragna.core.Chat.answer]ed.

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

    async def answer(self, prompt: str):
        """Answer a prompt

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

        # FIXME:
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
                document = self._rag.config.rag.document(document)

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
                raw_field_definitions[name].append(
                    (field.annotation, field.is_required())
                )

        field_definitions = {}
        for name, definitions in raw_field_definitions.items():
            types, requireds = zip(*definitions)

            types = set(types)
            if len(types) > 1:
                raise RagnaException(f"Mismatching types for field {name}: {types}")
            type_ = types.pop()

            default = ... if any(requireds) else None

            field_definitions[name] = (type_, default)

        return create_model(
            str(self), __config__=ConfigDict(extra=Extra.forbid), **field_definitions
        )

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
