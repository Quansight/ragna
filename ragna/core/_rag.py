from __future__ import annotations

import datetime
import itertools
import subprocess
import sys
from collections import defaultdict
from typing import Any, Optional, Sequence, TypeVar

from pydantic import BaseModel, create_model, Extra

from ._assistant import Message

from ._component import RagComponent
from ._config import Config
from ._exceptions import RagnaException
from ._queue import _enqueue_job, _get_queue
from ._source_storage import Document
from ._state import State

T = TypeVar("T", bound=RagComponent)


class Rag:
    def __init__(
        self,
        config: Optional[Config] = None,
        *,
        start_redis_server: Optional[bool] = None,
        start_ragna_worker: bool | int = True,
        deselect_unavailable_components=True,
    ):
        self.config = config or Config()
        self._logger = self.config.get_logger()

        self._state = State(self.config.state_database_url)

        self._subprocesses = set()
        self._queue, redis_server_proc = _get_queue(
            self.config.queue_database_url, start_redis_server=start_redis_server
        )
        if redis_server_proc is not None:
            self._logger.info("Started redis server")
            self._subprocesses.add(redis_server_proc)
        ragna_worker_proc = self._start_ragna_worker(start_ragna_worker)
        if ragna_worker_proc is not None:
            self._logger.info("Started ragna worker")
            self._subprocesses.add(ragna_worker_proc)

        self._source_storages = self._load_components(
            self.config.registered_source_storage_classes,
            deselect_unavailable_components=deselect_unavailable_components,
        )
        self._assistants = self._load_components(
            self.config.registered_assistant_classes,
            deselect_unavailable_components=deselect_unavailable_components,
        )

        self._chats: dict[(str, str), Chat] = {}

    def _add_document(self, *, user: str, id: str, name: str, metadata):
        self._state.add_document(user=user, id=id, name=name, metadata=metadata)

    def _get_document(self, user: str, id: str):
        data = self._state.get_document(user=user, id=id)
        if data is None:
            raise RagnaException
        return self.config.document_class(
            id=id, name=data.name, metadata=data.metadata_
        )

    async def _get_chats(self, *, user: str):
        chats = [
            Chat(
                rag=self,
                user=user,
                id=data.id,
                name=data.name,
                documents=[
                    self.config.document_class(
                        id=document_data.id,
                        name=document_data.name,
                        metadata=document_data.metadata_,
                    )
                    for document_data in data.document_datas
                ],
                source_storage=self._parse_component(
                    data.source_storage, registry=self._source_storages
                ),
                assistant=self._parse_component(
                    data.assistant, registry=self._assistants
                ),
                **data.params,
            )
            for data in self._state.get_chats(user=user)
        ]
        self._chats.update({(user, chat.id): chat for chat in chats})
        return chats

    async def _get_chat(self, *, user: str, id: str):
        key = (user, id)

        chat = self._chats.get(key)
        if chat is not None:
            return chat

        await self._get_chats(user=user)
        chat = self._chats.get(key)
        if chat is not None:
            raise chat

        raise RagnaException

    async def new_chat(
        self,
        *,
        user: str = "Ragna",
        name: Optional[str] = None,
        documents: Sequence[Any],
        source_storage: Any,
        assistant: Any,
        **params,
    ):
        documents = self._parse_documents(documents, user=user)
        source_storage = self._parse_component(
            source_storage, registry=self._source_storages
        )
        assistant = self._parse_component(assistant, registry=self._assistants)

        chat = Chat(
            rag=self,
            user=user,
            id=self._state.make_id(),
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
            source_storage=str(source_storage),
            assistant=str(assistant),
            params=params,
        )

        return chat

    def _start_ragna_worker(self, start: bool | int):
        # FIXME: can we detect if any workers are subscribed to the queue? If so, let's
        #  make the default value None, which means we only start if there is no other
        #  worker

        if not start:
            return None

        # FIXME: Maybe this needs to take the config as whole? If not at least the URL
        proc = subprocess.Popen(
            [sys.executable, "-m", "ragna", "worker", "--num-workers", str(int(start))],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            # FIXME: there needs to be a better way to check this.
            stdout, stderr = proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            # This means the worker process did not shut down and thus seems to be
            # running
            return proc
        else:
            raise RagnaException(
                f"Worker process terminated unexpectedly {stdout} {stderr}"
            )

    def _load_components(
        self, component_classes: dict, *, deselect_unavailable_components
    ):
        components = {}
        deselected = False
        for name, component_class in component_classes.items():
            if not component_class.is_available():
                self._logger.warn("Component not available", name=name)
                deselected = True
                continue

            components[name] = component_class(self.config)

        if deselected and not deselect_unavailable_components:
            raise RagnaException()

        if not components:
            self._logger.warning("No registered components available")

        return components

    def _parse_documents(self, document: Sequence[Any], *, user: str) -> list[Document]:
        documents_ = []
        for document in document:
            if self._state.is_id(document):
                document = self._get_document(id=document, user=user)
            else:
                if not isinstance(document, Document):
                    document = self.config.document_class(document)

                if document.id is None:
                    document.id = self._state.make_id()
                    self._add_document(
                        user=user,
                        id=document.id,
                        name=document.name,
                        metadata=document.metadata,
                    )

            if not document.is_available():
                raise RagnaException()

            documents_.append(document)
        return documents_

    def _parse_component(self, obj: Any, *, registry: dict[str, T]) -> T:
        if isinstance(obj, RagComponent):
            return obj
        elif isinstance(obj, type) and issubclass(obj, RagComponent):
            if not obj.is_available():
                raise RagnaException(obj)
            return obj(self.config)
        elif obj in registry:
            return registry[obj]
        else:
            raise RagnaException(obj)

    def __del__(self):
        for proc in self._subprocesses:
            proc.kill()
        for proc in self._subprocesses:
            proc.communicate()


class Chat:
    def __init__(
        self,
        *,
        rag: Rag,
        user: str,
        id: str,
        name: Optional[str] = None,
        documents,
        source_storage,
        assistant,
        **params,
    ):
        self._rag = rag
        self._user = user
        self.id = id
        self.name = name or f"{datetime.datetime.now():%c}"
        self.documents = documents
        self.source_storage = source_storage
        self.assistant = assistant

        self.params = params
        self._unpacked_params = self._unpack_chat_params(params)

        self.messages: list[Message] = []

        self._started = False
        self._closed = False

    async def start(self):
        if self._started:
            raise RagnaException()
        elif self._closed:
            raise RagnaException()

        await self._enqueue(self.source_storage.store, self.documents)
        self._rag._state.start_chat(user=self._user, id=self.id)
        self._started = True

    async def close(self):
        self._rag._state.close_chat(id=self.id, user=self._user)
        self._closed = True

    async def answer(self, prompt: str):
        if not self._started:
            raise RagnaException
        elif self._closed:
            raise RagnaException
        sources = await self._enqueue(self.source_storage.retrieve, prompt)
        content = await self._enqueue(self.assistant.answer, prompt, sources)
        self._rag._state.add_message(user=self._user, chat_id=self.id, content=content)
        return Answer(sources=sources, content=content)

    class _SpecialChatParams(BaseModel):
        user: str
        chat_id: str
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

        return {
            method: model(**chat_model.dict(exclude_none=True)).dict()
            for method, model in itertools.chain(
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

    async def _enqueue(self, fn, *args):
        unpacked_params = self._unpacked_params[fn]
        return await _enqueue_job(
            self._rag._queue,
            lambda: fn(*args, **unpacked_params),
            **getattr(fn, "__ragna_job_kwargs__", {}),
        )

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *_):
        # FIXME: does this suppress the exception?
        await self.close()
