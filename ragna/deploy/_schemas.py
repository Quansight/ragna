from __future__ import annotations

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, Field

import ragna.core


class User(BaseModel):
    name: str
    data: dict[str, Any] = Field(default_factory=dict)


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
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


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
