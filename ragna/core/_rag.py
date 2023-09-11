from __future__ import annotations

import datetime
import itertools

import subprocess
import sys
from collections import defaultdict

from typing import Any, Optional, Sequence, TypeVar

from pydantic import BaseModel, create_model, Extra

from ._component import Component

from ._config import Config
from ._exceptions import RagnaException

from ._queue import _enqueue_job, _get_queue
from ._source_storage import Document

from ._state import State

T = TypeVar("T", bound=Component)


class Rag:
    def __init__(
        self,
        config: Optional[Config] = None,
        *,
        start_redis_server: Optional[bool] = None,
        start_ragna_worker: bool = False,
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
            self._subprocesses.add(redis_server_proc)

        # FIXME: can we detect if any workers are subscribed to the queue? If so, let's
        #  make the default value None, which means we only start if there is no other
        #  worker
        if start_ragna_worker:
            # FIXME: Maybe this needs to take the config as whole? If not at least the URL
            proc = subprocess.Popen([sys.executable, "-m", "ragna", "worker"])
            try:
                stdout, stderr = proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                # This means the worker process did not shut down and thus seems to be
                # running
                self._subprocesses.add(proc)
            else:
                raise RagnaException(
                    f"Worker process terminated unexpectedly {stdout} {stderr}"
                )

        self._source_storages = self._load_components(
            self.config.registered_source_storage_classes,
            deselect_unavailable_components=deselect_unavailable_components,
        )
        self._llms = self._load_components(
            self.config.registered_llm_classes,
            deselect_unavailable_components=deselect_unavailable_components,
        )

        self._chats: dict[int, Chat] = {}

    def __del__(self):
        for proc in self._subprocesses:
            proc.kill()
            proc.communicate()

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

    async def add_document(self, *, user: str, document: Document):
        if document.id is not None:
            raise RagnaException()

        data = self._state.add_document(
            user=user, name=document.name, metadata=document.metadata
        )
        return data.id

    async def start_new_chat(
        self,
        *,
        user: str = "root",
        name: Optional[str] = None,
        documents: Sequence[Any],
        source_storage: Any,
        llm: Any,
        **params,
    ):
        documents = await self._parse_documents(documents, user=user)
        source_storage = self._parse_component(
            source_storage, registry=self._source_storages
        )
        llm = self._parse_component(llm, registry=self._llms)

        chat = Chat(
            rag=self,
            user=user,
            id=self._state.make_id(),
            name=name,
            documents=documents,
            source_storage=source_storage,
            llm=llm,
            **params,
        )

        self._state.add_chat(
            id=chat.id,
            user=user,
            name=chat.name,
            document_ids=[document.id for document in documents],
            source_storage_name=str(source_storage),
            llm_name=str(llm),
            params=params,
        )

        await chat.start()

        return chat

    async def _parse_documents(
        self, objs: Sequence[Any], *, user: str
    ) -> list[Document]:
        documents_ = []
        for obj in objs:
            if isinstance(obj, Document):
                document = obj
            else:
                if self._state.is_id(obj):
                    data = self._state.get_document(id=obj, user=user)
                    if data is None:
                        raise RagnaException
                    document = self.config.document_class._from_data(data)
                else:
                    document = self.config.document_class(obj)

            if document.id is None:
                document.id = await self.add_document(user=user, document=document)

            documents_.append(document)
        return documents_

    def _parse_component(self, obj: Any, *, registry: dict[str, T]) -> T:
        if isinstance(obj, Component):
            return obj
        elif isinstance(obj, type) and issubclass(obj, Component):
            if not obj.is_available():
                raise RagnaException(obj)
            return obj(self.config)
        elif obj in registry:
            return registry[obj]
        else:
            raise RagnaException(obj)


# TOD: Make this a context manager and implement a close functionality
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
        llm,
        **params,
    ):
        self._rag = rag
        self._user = user
        self.id = id
        self.name = name or f"{datetime.datetime.now():%c}"
        self.documents = documents
        self.source_storage = source_storage
        self.llm = llm

        self.params = params
        self._unpacked_params = self._unpack_chat_params(params)

    def __repr__(self):
        return f"{type(self).__name__}(id={self.id}, name={self.name})"

    class _SpecialChatParams(BaseModel):
        user: str
        chat_id: str
        chat_name: str

    def _unpack_chat_params(self, params):
        source_storage_models = self.source_storage._models()
        llm_models = self.llm._models()

        ChatModel = self._merge_models(
            self._SpecialChatParams,
            *source_storage_models.values(),
            *llm_models.values(),
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
                source_storage_models.items(), llm_models.items()
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

    @property
    def _logger(self):
        return self._rag._logger

    @property
    def _state(self):
        return self._rag._state

    async def _enqueue(self, fn, *args):
        unpacked_params = self._unpacked_params[fn]
        return await _enqueue_job(
            self._rag._queue,
            lambda: fn(*args, **unpacked_params),
            **getattr(fn, "__ragna_job_kwargs__", {}),
        )

    async def start(self):
        return await self._enqueue(self.source_storage.store, self.documents)

    async def answer(self, prompt: str):
        sources = await self._enqueue(self.source_storage.retrieve, prompt)
        answer = await self._enqueue(self.llm.complete, prompt, sources)
        self._state.add_message(user=self._user, chat_id=self.id, content=answer)
        return answer
