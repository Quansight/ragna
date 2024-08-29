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


class Document(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str

    @classmethod
    def from_core(cls, document: ragna.core.Document) -> Document:
        return cls(
            id=document.id,
            name=document.name,
        )

    def to_core(self) -> ragna.core.Document:
        return ragna.core.LocalDocument(
            id=self.id,
            name=self.name,
            # TEMP: setting an empty metadata dict for now.
            # Will be resolved as part of the "managed ragna" work:
            # https://github.com/Quansight/ragna/issues/256
            metadata={},
        )


class DocumentUpload(BaseModel):
    parameters: ragna.core.DocumentUploadParameters
    document: Document


class Source(BaseModel):
    # See orm.Source on why this is not a UUID
    id: str
    document: Document
    location: str
    content: str
    num_tokens: int

    @classmethod
    def from_core(cls, source: ragna.core.Source) -> Source:
        return cls(
            id=source.id,
            document=Document.from_core(source.document),
            location=source.location,
            content=source.content,
            num_tokens=source.num_tokens,
        )

    def to_core(self) -> ragna.core.Source:
        return ragna.core.Source(
            id=self.id,
            document=self.document.to_core(),
            location=self.location,
            content=self.content,
            num_tokens=self.num_tokens,
        )


class Message(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    content: str
    role: ragna.core.MessageRole
    sources: list[Source] = Field(default_factory=list)
    timestamp: UtcDateTime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_core(cls, message: ragna.core.Message) -> Message:
        return cls(
            content=message.content,
            role=message.role,
            sources=[Source.from_core(source) for source in message.sources],
        )

    def to_core(self) -> ragna.core.Message:
        return ragna.core.Message(
            content=self.content,
            role=self.role,
            sources=[source.to_core() for source in self.sources],
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
