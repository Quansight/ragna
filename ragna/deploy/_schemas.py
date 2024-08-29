from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, Field

import ragna.core


def _set_utc_timezone(v: datetime) -> datetime:
    if v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    else:
        return v.astimezone(timezone.utc)


UtcDateTime = Annotated[datetime, AfterValidator(_set_utc_timezone)]


class Components(BaseModel):
    documents: list[str]
    source_storages: list[dict[str, Any]]
    assistants: list[dict[str, Any]]


class DocumentRegistration(BaseModel):
    name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    metadata: dict[str, Any]


class Source(BaseModel):
    # See orm.Source on why this is not a UUID
    id: str
    document: Document
    location: str
    content: str
    num_tokens: int


class Message(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    content: str
    role: ragna.core.MessageRole
    sources: list[Source] = Field(default_factory=list)
    timestamp: UtcDateTime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatCreation(BaseModel):
    name: str
    document_ids: list[uuid.UUID]
    source_storage: str
    assistant: str
    params: dict[str, Any] = Field(default_factory=dict)


class Chat(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    documents: list[Document]
    source_storage: str
    assistant: str
    params: dict[str, Any]
    messages: list[Message] = Field(default_factory=list)
    prepared: bool = False
