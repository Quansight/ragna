from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    ValidationInfo,
    computed_field,
    field_validator,
)

import ragna.core


class User(BaseModel):
    name: str
    data: dict[str, Any] = Field(default_factory=dict)


class ApiKeyCreation(BaseModel):
    name: str
    expires_at: datetime


class ApiKey(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    expires_at: datetime
    obfuscated: bool = True
    value: str

    @field_validator("expires_at")
    @classmethod
    def _set_utc_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        else:
            return v.astimezone(timezone.utc)

    @computed_field  # type: ignore[misc]
    @property
    def expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    @field_validator("value")
    @classmethod
    def _maybe_obfuscate(cls, v: str, info: ValidationInfo) -> str:
        if not info.data["obfuscated"]:
            return v

        i = min(len(v) // 6, 3)
        if i > 0:
            return f"{v[:i]}***{v[-i:]}"
        else:
            return "***"


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
    document_id: uuid.UUID
    document_name: str
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
    input: None | ragna.core.MetadataFilter | list[uuid.UUID] = None
    source_storage: str
    assistant: str
    corpus_name: str = "default"
    params: dict[str, Any] = Field(default_factory=dict)


class Chat(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    metadata_filter: ragna.core.MetadataFilter | None
    documents: list[Document] | None
    source_storage: str
    assistant: str
    corpus_name: str = "default"
    params: dict[str, Any]
    messages: list[Message] = Field(default_factory=list)
    prepared: bool = False
