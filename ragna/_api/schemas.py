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
    def from_core_source(cls, source: ragna.core.Source) -> Source:
        return cls(
            id=source.id,
            document=Document(id=source.document_id, name=source.document_name),
            location=source.location,
        )


class Message(BaseModel):
    id: ragna.core.RagnaId
    role: ragna.core.MessageRole
    content: str
    sources: list[Source]
    timestamp: datetime.datetime

    @classmethod
    def from_core_message(cls, message: ragna.core.Message) -> Message:
        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            sources=[Source.from_core_source(s) for s in message.sources],
            timestamp=message.timestamp,
        )


class ChatMetadataBase(BaseModel):
    name: str
    source_storage: str
    assistant: str
    params: dict


class ChatMetadataCreate(ChatMetadataBase):
    # For some reason list[RagnaId] does not work and will get parsed into list[UUID].
    # Thus, we use a validator below to do the conversion.
    document_ids: list[UUID]

    @validator("document_ids")
    def uuid_to_ragna_id(cls, document_ids: list[UUID]) -> list[ragna.core.RagnaId]:
        return [ragna.core.RagnaId.from_uuid(u) for u in document_ids]


class ChatMetadata(ChatMetadataBase):
    documents: list[Document]

    @classmethod
    def from_core_chat(cls, chat: ragna.core.Chat) -> ChatMetadata:
        return cls(
            name=chat.name,
            documents=[Document.from_core_document(d) for d in chat.documents],
            source_storage=chat.source_storage.display_name(),
            assistant=chat.assistant.display_name(),
            params=chat.params,
        )


class Chat(BaseModel):
    id: ragna.core.RagnaId
    metadata: ChatMetadata
    messages: list[Message]
    started: bool
    closed: bool

    @classmethod
    def from_core_chat(cls, chat: ragna.core.Chat) -> Chat:
        return cls(
            id=chat.id,
            metadata=ChatMetadata.from_core_chat(chat),
            messages=[Message.from_core_message(m) for m in chat.messages],
            started=chat._started,
            closed=chat._closed,
        )


class AnswerOutput(BaseModel):
    message: Message
    chat: Chat


class Components(BaseModel):
    source_storages: list[str]
    assistants: list[str]
