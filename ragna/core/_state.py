from __future__ import annotations

import functools
import re
import uuid
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    create_engine,
    Enum,
    ForeignKey,
    JSON,
    select,
    String,
    Table,
)

from sqlalchemy.orm import DeclarativeBase, relationship, Session

from ragna.core import MessageRole, Source

from ._exceptions import RagnaException


class Base(DeclarativeBase):
    pass


def _make_id() -> str:
    return str(uuid.uuid4())


# FIXME: try and use this
class RagnaId(str):
    pass


# FIXME Make this actual UUID columns?
# FIXME: do we actually need this?
class UserData(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    name = Column(String)


document_chat_data_association_table = Table(
    "document_chat_data_association_table",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("chat_id", ForeignKey("chats.id"), primary_key=True),
)


# Name this state?
class DocumentData(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    name = Column(String)
    # Mind the trailing underscore here. Unfortunately, this is necessary, because
    # metadata without the underscore is reserved by SQLAlchemy
    metadata_ = Column(JSON)
    chat_datas = relationship(
        "ChatData",
        secondary=document_chat_data_association_table,
        back_populates="document_datas",
    )
    source_datas = relationship(
        "SourceData",
        back_populates="document_data",
    )


class ChatData(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    name = Column(String)
    document_datas = relationship(
        "DocumentData",
        secondary=document_chat_data_association_table,
        back_populates="chat_datas",
    )
    source_storage = Column(String)
    assistant = Column(String)
    params = Column(JSON)
    message_datas = relationship("MessageData", cascade="all, delete")
    started = Column(Boolean)
    closed = Column(Boolean)


source_message_data_association_table = Table(
    "source_message_data_association_table",
    Base.metadata,
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
    Column("message_id", ForeignKey("messages.id"), primary_key=True),
)


class SourceData(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True)

    document_id = Column(ForeignKey("documents.id"))
    document_data = relationship("DocumentData", back_populates="source_datas")

    location = Column(String)

    message_datas = relationship(
        "MessageData",
        secondary=source_message_data_association_table,
        back_populates="source_datas",
    )


class MessageData(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    chat_id = Column(ForeignKey("chats.id"))
    content = Column(String)
    role = Column(Enum(MessageRole))
    source_id = Column(ForeignKey("sources.id"))
    source_datas = relationship(
        "SourceData",
        secondary=source_message_data_association_table,
        back_populates="message_datas",
    )


# FIXME: user first in all signatures!
class State:
    def __init__(self, url: str):
        self._engine = create_engine(url)
        Base.metadata.create_all(self._engine)
        self._session = Session(self._engine)

    def __del__(self):
        if hasattr(self, "_session"):
            self._session.close()

    def make_id(self):
        return _make_id()

    _UUID_STR_PATTERN = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )

    def is_id(self, obj: Any) -> bool:
        if not isinstance(obj, str):
            return False

        return self._UUID_STR_PATTERN.match(obj) is not None

    @functools.lru_cache(maxsize=1024)
    def _get_user_id(self, username: str):
        user_id = self._session.execute(
            select(UserData.id).where(UserData.name == username)
        ).scalar_one_or_none()
        if user_id is not None:
            return user_id

        user = UserData(id=_make_id(), name=username)
        self._session.add(user)
        self._session.commit()
        return user.id

    def add_document(self, *, id: str, user: str, name: str, metadata: dict[str, Any]):
        document_data = DocumentData(
            id=id,
            user_id=self._get_user_id(user),
            name=name,
            metadata_=metadata,
        )
        self._session.add(document_data)
        self._session.commit()
        return document_data

    def get_document(self, id: str, user: str) -> DocumentData:
        return self._session.execute(
            select(DocumentData).where(
                (DocumentData.id == id)
                & (DocumentData.user_id == self._get_user_id(user))
            )
        ).scalar_one_or_none()

    def get_chats(self, user: str):
        # Add filters for started and closed here
        return (
            self._session.execute(
                select(ChatData).where(ChatData.user_id == self._get_user_id(user))
            )
            .scalars()
            .all()
        )

    def add_chat(
        self,
        *,
        # FIXME: always generate IDs on the OUTSIDE
        # This takes the ID instead of generating it itself, because we need to create
        # the Chat object before we add it to the database
        id: str,
        user: str,
        name: str,
        document_ids: list[str],
        source_storage: str,
        assistant: str,
        params,
    ) -> ChatData:
        document_datas = (
            self._session.execute(
                select(DocumentData).where(DocumentData.id.in_(document_ids))
            )
            .scalars()
            .all()
        )
        if len(document_datas) != len(document_ids):
            raise RagnaException(
                set(document_ids) - {document.id for document in document_datas}
            )
        chat = ChatData(
            id=id,
            user_id=self._get_user_id(user),
            name=name,
            document_datas=document_datas,
            source_storage=source_storage,
            assistant=assistant,
            params=params,
            started=False,
            closed=False,
        )
        self._session.add(chat)
        self._session.commit()
        return chat

    def _get_chat(self, *, user: str, id: str):
        chat_data = self._session.execute(
            select(ChatData).where(
                (ChatData.id == id) & (ChatData.user_id == self._get_user_id(user))
            )
        ).scalar_one_or_none()
        if chat_data is None:
            raise RagnaException()
        return chat_data

    def start_chat(self, *, id: str, user: str):
        chat_data = self._get_chat(user=user, id=id)
        chat_data.started = True
        self._session.commit()

    def close_chat(self, *, id: str, user: str):
        chat_data = self._get_chat(user=user, id=id)
        chat_data.closed = True
        self._session.commit()

    def add_message(
        self,
        *,
        user: str,
        chat_id: str,
        id: str,
        content: str,
        role: MessageRole,
        sources: Optional[list[Source]] = None,
    ):
        chat_data = self._session.execute(
            select(ChatData).where(
                (ChatData.user_id == self._get_user_id(user)) & (ChatData.id == chat_id)
            )
        ).scalar_one_or_none()
        if chat_data is None:
            raise RagnaException

        print(sources)

        if sources is not None:
            source_datas = (
                self._session.execute(
                    select(SourceData).where(
                        SourceData.id.in_([source.id for source in sources])
                    )
                )
                .scalars()
                .all()
            )
        else:
            source_datas = []

        message_data = MessageData(
            id=id,
            chat_id=chat_data.id,
            content=content,
            role=role,
            source_datas=source_datas,
        )
        chat_data.message_datas.append(message_data)
        self._session.commit()
