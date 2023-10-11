from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, Field, HttpUrl

import ragna.core


class Components(BaseModel):
    source_storages: list[str]
    assistants: list[str]


class Document(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str


class DocumentUploadInfo(BaseModel):
    url: HttpUrl
    data: dict
    document: Document


# two reasons not to subclass
# 1. we use the Document model rather than split on core
# 2. core includes actual document content that we don't want to leak
class Source(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    document: Document
    location: str


class Message(ragna.core.Message):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime.datetime = Field(
        default_factory=datetime.datetime.now(tz=datetime.timezone.utc)
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
