import uuid
from typing import Any, AsyncIterator, Optional, Type, cast

from fastapi import status as http_status_code

import ragna
from ragna import Rag, core
from ragna._compat import aiter, anext
from ragna._utils import make_directory
from ragna.core import RagnaException
from ragna.core._rag import SpecialChatParams
from ragna.deploy import Config

from . import _schemas as schemas
from ._database import Database


class Engine:
    def __init__(self, *, config: Config, ignore_unavailable_components: bool) -> None:
        self._config = config
        ragna.local_root(config.local_root)
        self._documents_root = make_directory(config.local_root / "documents")
        self.supports_store_documents = issubclass(
            self._config.document, ragna.core.LocalDocument
        )

        self._database = Database(url=config.database_url)

        self._rag = Rag(  # type: ignore[var-annotated]
            config=config,
            ignore_unavailable_components=ignore_unavailable_components,
        )

        self._to_core = SchemaToCoreConverter(config=self._config, rag=self._rag)
        self._to_schema = CoreToSchemaConverter()

    def _get_component_json_schema(
        self,
        component: Type[core.Component],
    ) -> dict[str, dict[str, Any]]:
        json_schema = component._protocol_model().model_json_schema()
        # FIXME: there is likely a better way to exclude certain fields builtin in
        #  pydantic
        for special_param in SpecialChatParams.model_fields:
            if (
                "properties" in json_schema
                and special_param in json_schema["properties"]
            ):
                del json_schema["properties"][special_param]
            if "required" in json_schema and special_param in json_schema["required"]:
                json_schema["required"].remove(special_param)
        return json_schema

    def get_components(self) -> schemas.Components:
        return schemas.Components(
            documents=sorted(self._config.document.supported_suffixes()),
            source_storages=[
                self._get_component_json_schema(source_storage)
                for source_storage in self._rag._components.keys()
                if issubclass(source_storage, core.SourceStorage)
            ],
            assistants=[
                self._get_component_json_schema(assistant)
                for assistant in self._rag._components.keys()
                if issubclass(assistant, core.Assistant)
            ],
        )

    def register_documents(
        self, *, user: str, document_registrations: list[schemas.DocumentRegistration]
    ) -> list[schemas.Document]:
        # We create core.Document's first, because they might update the metadata
        core_documents = [
            self._config.document(
                name=registration.name, metadata=registration.metadata
            )
            for registration in document_registrations
        ]
        documents = [self._to_schema.document(document) for document in core_documents]

        with self._database.get_session() as session:
            self._database.add_documents(session, user=user, documents=documents)

        return documents

    async def store_documents(
        self,
        *,
        user: str,
        ids_and_streams: list[tuple[uuid.UUID, AsyncIterator[bytes]]],
    ) -> None:
        if not self.supports_store_documents:
            raise RagnaException(
                "Ragna configuration does not support local upload",
                http_status_code=http_status_code.HTTP_400_BAD_REQUEST,
            )

        ids, streams = zip(*ids_and_streams)

        with self._database.get_session() as session:
            documents = self._database.get_documents(session, user=user, ids=ids)

        for document, stream in zip(documents, streams):
            core_document = cast(
                ragna.core.LocalDocument, self._to_core.document(document)
            )
            await core_document._write(stream)

    def create_chat(
        self, *, user: str, chat_creation: schemas.ChatCreation
    ) -> schemas.Chat:
        params = chat_creation.model_dump()
        document_ids = params.pop("document_ids")
        with self._database.get_session() as session:
            documents = self._database.get_documents(
                session, user=user, ids=document_ids
            )

        chat = schemas.Chat(documents=documents, **params)

        # Although we don't need the actual core.Chat here, this performs the input
        # validation.
        self._to_core.chat(chat, user=user)

        with self._database.get_session() as session:
            self._database.add_chat(session, user=user, chat=chat)

        return chat

    def get_chats(self, *, user: str) -> list[schemas.Chat]:
        with self._database.get_session() as session:
            return self._database.get_chats(session, user=user)

    def get_chat(self, *, user: str, id: uuid.UUID) -> schemas.Chat:
        with self._database.get_session() as session:
            return self._database.get_chat(session, user=user, id=id)

    async def prepare_chat(self, *, user: str, id: uuid.UUID) -> schemas.Message:
        core_chat = self._to_core.chat(self.get_chat(user=user, id=id), user=user)
        core_message = await core_chat.prepare()

        with self._database.get_session() as session:
            self._database.update_chat(
                session, chat=self._to_schema.chat(core_chat), user=user
            )

        return self._to_schema.message(core_message)

    async def answer_stream(
        self, *, user: str, chat_id: uuid.UUID, prompt: str
    ) -> AsyncIterator[schemas.Message]:
        core_chat = self._to_core.chat(self.get_chat(user=user, id=chat_id), user=user)
        core_message = await core_chat.answer(prompt, stream=True)

        content_stream = aiter(core_message)
        content_chunk = await anext(content_stream)
        message = self._to_schema.message(core_message, content_override=content_chunk)
        yield message

        # Avoid sending the sources multiple times
        message_chunk = message.model_copy(update=dict(sources=None))
        async for content_chunk in content_stream:
            message_chunk.content = content_chunk
            yield message_chunk

        with self._database.get_session() as session:
            self._database.update_chat(
                session, chat=self._to_schema.chat(core_chat), user=user
            )

    def delete_chat(self, *, user: str, id: uuid.UUID) -> None:
        with self._database.get_session() as session:
            self._database.delete_chat(session, user=user, id=id)


class SchemaToCoreConverter:
    def __init__(self, *, config: Config, rag: Rag) -> None:
        self._config = config
        self._rag = rag

    def document(self, document: schemas.Document) -> core.Document:
        return self._config.document(
            id=document.id,
            name=document.name,
            metadata=document.metadata,
        )

    def source(self, source: schemas.Source) -> core.Source:
        return core.Source(
            id=source.id,
            document=self.document(source.document),
            location=source.location,
            content=source.content,
            num_tokens=source.num_tokens,
        )

    def message(self, message: schemas.Message) -> core.Message:
        return core.Message(
            message.content,
            role=message.role,
            sources=[self.source(source) for source in message.sources],
        )

    def chat(self, chat: schemas.Chat, *, user: str) -> core.Chat:
        core_chat = self._rag.chat(
            user=user,
            chat_id=chat.id,
            chat_name=chat.name,
            documents=[self.document(document) for document in chat.documents],
            source_storage=chat.source_storage,
            assistant=chat.assistant,
            **chat.params,
        )
        core_chat._messages = [self.message(message) for message in chat.messages]
        core_chat._prepared = chat.prepared

        return core_chat


class CoreToSchemaConverter:
    def document(self, document: core.Document) -> schemas.Document:
        return schemas.Document(
            id=document.id,
            name=document.name,
            metadata=document.metadata,
        )

    def source(self, source: core.Source) -> schemas.Source:
        return schemas.Source(
            id=source.id,
            document=self.document(source.document),
            location=source.location,
            content=source.content,
            num_tokens=source.num_tokens,
        )

    def message(
        self, message: core.Message, *, content_override: Optional[str] = None
    ) -> schemas.Message:
        return schemas.Message(
            id=message.id,
            content=(
                content_override if content_override is not None else message.content
            ),
            role=message.role,
            sources=[self.source(source) for source in message.sources],
            timestamp=message.timestamp,
        )

    def chat(self, chat: core.Chat) -> schemas.Chat:
        params = chat.params.copy()
        del params["user"]
        return schemas.Chat(
            id=params.pop("chat_id"),
            name=params.pop("chat_name"),
            documents=[self.document(document) for document in chat.documents],
            source_storage=chat.source_storage.display_name(),
            assistant=chat.assistant.display_name(),
            params=params,
            messages=[self.message(message) for message in chat._messages],
            prepared=chat._prepared,
        )
