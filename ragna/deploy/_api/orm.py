import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, ForeignKey, Table, types
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, relationship  # type: ignore[attr-defined]

from ragna.core import MessageRole


class Json(types.TypeDecorator):
    """Universal JSON type which stores values as strings.

    This is needed because sqlalchemy.types.JSON only works for a limited subset of
    databases.
    """

    impl = types.String

    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str:
        return json.dumps(value)

    def process_result_value(
        self,
        value: str,  # type: ignore[override]
        dialect: Dialect,
    ) -> Any:
        return json.loads(value)


class UtcDateTime(types.TypeDecorator):
    """UTC timezone aware datetime type.

    This is needed because sqlalchemy.types.DateTime(timezone=True) does not
    consistently store the timezone.
    """

    impl = types.DateTime

    cache_ok = True

    def process_bind_param(  # type: ignore[override]
        self, value: Optional[datetime], dialect: Dialect
    ) -> Optional[datetime]:
        if value is not None:
            assert value.tzinfo == timezone.utc

        return value

    def process_result_value(
        self, value: Optional[datetime], dialect: Dialect
    ) -> Optional[datetime]:
        if value is None:
            return None

        return value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass


# FIXME: Do we actually need this table? If we are sure that a user is unique and has to
#  be authenticated from the API layer, it seems having an extra mapping here is not
#  needed?
class User(Base):
    __tablename__ = "users"

    id = Column(types.Uuid, primary_key=True)  # type: ignore[attr-defined]
    name = Column(types.String, nullable=False)


document_chat_association_table = Table(
    "document_chat_association_table",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("chat_id", ForeignKey("chats.id"), primary_key=True),
)


class Document(Base):
    __tablename__ = "documents"

    id = Column(types.Uuid, primary_key=True)  # type: ignore[attr-defined]
    user_id = Column(ForeignKey("users.id"))
    name = Column(types.String, nullable=False)
    # Mind the trailing underscore here. Unfortunately, this is necessary, because
    # metadata without the underscore is reserved by SQLAlchemy
    metadata_ = Column(Json, nullable=False)
    chats = relationship(
        "Chat",
        secondary=document_chat_association_table,
        back_populates="documents",
    )
    sources = relationship(
        "Source",
        back_populates="document",
    )


class Chat(Base):
    __tablename__ = "chats"

    id = Column(types.Uuid, primary_key=True)  # type: ignore[attr-defined]
    user_id = Column(ForeignKey("users.id"))
    name = Column(types.String, nullable=False)
    documents = relationship(
        "Document",
        secondary=document_chat_association_table,
        back_populates="chats",
    )
    source_storage = Column(types.String, nullable=False)
    assistant = Column(types.String, nullable=False)
    params = Column(Json, nullable=False)
    messages = relationship(
        "Message", cascade="all, delete", order_by="Message.timestamp"
    )
    prepared = Column(types.Boolean, nullable=False)


source_message_association_table = Table(
    "source_message_association_table",
    Base.metadata,
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
    Column("message_id", ForeignKey("messages.id"), primary_key=True),
)


class Source(Base):
    __tablename__ = "sources"

    # This is not a UUID column as all of the other IDs, because we don't control its
    # generation. It is generated as part of ragna.core.SourceStorage.retrieve and using
    # a string here doesn't impose unnecessary constraints on the user.
    id = Column(types.String, primary_key=True)

    document_id = Column(ForeignKey("documents.id"))
    document = relationship("Document", back_populates="sources")

    location = Column(types.String, nullable=False)
    content = Column(types.String, nullable=False)
    num_tokens = Column(types.Integer, nullable=False)

    messages = relationship(
        "Message",
        secondary=source_message_association_table,
        back_populates="sources",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(types.Uuid, primary_key=True)  # type: ignore[attr-defined]
    chat_id = Column(ForeignKey("chats.id"))
    content = Column(types.String, nullable=False)
    role = Column(types.Enum(MessageRole), nullable=False)
    sources = relationship(
        "Source",
        secondary=source_message_association_table,
        back_populates="messages",
    )
    timestamp = Column(UtcDateTime, nullable=False)
