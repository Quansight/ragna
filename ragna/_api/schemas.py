from __future__ import annotations

import datetime
from uuid import UUID

from pydantic import BaseModel, HttpUrl, validator

import ragna

import ragna.core


class Document(BaseModel):
    id: ragna.core.RagnaId
    name: str


class DocumentUploadInfo(BaseModel):
    url: HttpUrl
    data: dict
    document: Document


class Source(BaseModel):
    id: ragna.core.RagnaId
    document: Document
    location: str

    @classmethod
    def from_core_source(cls, core_source: ragna.core.Source) -> Source:
        return cls(
            id=core_source.id,
            document=Document(
                id=core_source.document_id, name=core_source.document_name
            ),
            location=core_source.location,
        )


class Message(BaseModel):
    id: ragna.core.RagnaId
    role: ragna.core.MessageRole
    content: str
    sources: list[Source]
    timestamp: datetime.datetime

    @classmethod
    def from_core_message(cls, core_message: ragna.core.Message) -> Message:
        return cls(
            id=core_message.id,
            role=core_message.role,
            content=core_message.content,
            sources=[Source.from_core_source(s) for s in core_message.sources],
            timestamp=core_message.timestamp,
        )


class ChatMetadataBase(BaseModel):
    name: str
    source_storage: str
    assistant: str
    params: dict


class ChatMetadataCreate(ChatMetadataBase):
    # For some reason list[RagnaId] does not work and will get parsed into list[UUID].
    # Thus, we use a validator below to do the conversion.
    document_ids: list[ragna.core.RagnaId]

    @validator("document_ids")
    def _uuid_to_ragna_id(cls, document_ids: list[UUID]) -> list[ragna.core.RagnaId]:
        return [ragna.core.RagnaId.from_uuid(u) for u in document_ids]


class ChatMetadata(ChatMetadataBase):
    documents: list[Document]

    @classmethod
    def from_core_chat(cls, core_chat: ragna.core.Chat) -> ChatMetadata:
        return cls(
            name=core_chat.name,
            documents=[Document.from_core_document(d) for d in core_chat.documents],
            source_storage=core_chat.source_storage.display_name(),
            assistant=core_chat.assistant.display_name(),
            params=core_chat.params,
        )


class Chat(BaseModel):
    id: ragna.core.RagnaId
    metadata: ChatMetadata
    messages: list[Message]
    started: bool
    closed: bool

    @classmethod
    def from_core_chat(cls, core_chat: ragna.core.Chat) -> Chat:
        return cls(
            id=core_chat.id,
            metadata=ChatMetadata.from_core_chat(core_chat),
            messages=[Message.from_core_message(m) for m in core_chat.messages],
            started=core_chat._started,
            closed=core_chat._closed,
        )

    def to_core_chat(self, rag: ragna.core.Rag) -> ragna.core.Chat:
        pass


class AnswerOutput(BaseModel):
    message: Message
    chat: Chat


class Components(BaseModel):
    source_storages: list[str]
    assistants: list[str]
