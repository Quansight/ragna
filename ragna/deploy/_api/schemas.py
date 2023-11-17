from __future__ import annotations

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, Field

import ragna.core


class Components(BaseModel):
    documents: list[str]
    source_storages: list[dict[str, Any]]
    assistants: list[dict[str, Any]]


class Document(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str

    @classmethod
    def from_core(cls, document: ragna.core.Document) -> Document:
        return cls(
            id=document.id,
            name=document.name,
        )


class DocumentUploadInfo(BaseModel):
    url: str
    data: dict
    document: Document


class Source(BaseModel):
    # See orm.Source on why this is not a UUID
    id: str
    document: Document
    location: str

    @classmethod
    def from_core(cls, source: ragna.core.Source) -> Source:
        return cls(
            id=source.id,
            document=Document.from_core(source.document),
            location=source.location,
        )


class Message(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    content: str
    role: ragna.core.MessageRole
    sources: list[Source] = Field(default_factory=list)
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.utcnow()
    )

    @classmethod
    def from_core(cls, message: ragna.core.Message) -> Message:
        return cls(
            content=message.content,
            role=message.role,
            sources=[Source.from_core(source) for source in message.sources],
        )


class ChatMetadata(BaseModel):
    name: str
    source_storage: str
    assistant: str
    params: dict
    documents: list[Document]


class Chat(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    metadata: ChatMetadata
    messages: list[Message] = Field(default_factory=list)
    prepared: bool = False


class MessageOutput(BaseModel):
    message: Message
    chat: Chat
