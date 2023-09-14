from __future__ import annotations

import functools
import re
import uuid
from typing import Any

from sqlalchemy import Column, create_engine, ForeignKey, JSON, select, Table

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    MappedAsDataclass,
    relationship,
    Session,
)

from ragna.core import MessageRole

from ._exceptions import RagnaException


class Base(MappedAsDataclass, DeclarativeBase):
    pass


def _make_id() -> str:
    return str(uuid.uuid4())


# FIXME: try and use this
class RagnaId(str):
    pass


# FIXME: do we actually need this?
class UserData(Base):
    __tablename__ = "users"

    # TODO: With Python >= 3.10, we could add
    #  (..., init=False, kw_only=True, default_factory=_make_id)
    # and thus avoid generating the id on the outside.
    # This doesn't work right now, because
    # 1. we can't have a field with default (id) before one without (name)
    # 2. kw_only will solve 1., but is only available for Python >= 3.10
    # Same for all other tables below
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]


document_chat_data_association_table = Table(
    "document_chat_data_association_table",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("chat_id", ForeignKey("chats.id"), primary_key=True),
)


class DocumentData(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    # Mind the trailing underscore here. Unfortunately, this is necessary, because
    # metadata without the underscore is reserved by SQLAlchemy
    metadata_: JSON
    chat_datas: Mapped[list[ChatData]] = relationship(
        secondary=document_chat_data_association_table,
        back_populates="document_datas",
        default_factory=list,
    )
    source_datas: Mapped[list[SourceData]] = relationship(
        back_populates="document_data",
        default_factory=list,
    )


class ChatData(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    document_datas: Mapped[list[DocumentData]] = relationship(
        secondary=document_chat_data_association_table,
        back_populates="chat_datas",
    )
    source_storage_name: Mapped[str]
    llm_name: Mapped[str]
    params: JSON
    message_datas: Mapped[list[MessageData]] = relationship(
        default_factory=list, cascade="all, delete"
    )
    closed: Mapped[bool] = mapped_column(default=False)


source_message_data_association_table = Table(
    "source_message_data_association_table",
    Base.metadata,
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
    Column("message_id", ForeignKey("messages.id"), primary_key=True),
)


class SourceData(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(primary_key=True)

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    document_data: Mapped[DocumentData] = relationship(back_populates="source_datas")

    location: Mapped[str]

    message_datas: Mapped[list[MessageData]] = relationship(
        secondary=source_message_data_association_table,
        back_populates="source_datas",
        default_factory=list,
    )


class MessageData(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(primary_key=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id"))
    content: Mapped[str]
    role: Mapped[MessageRole]
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    source_datas: Mapped[list[SourceData]] = relationship(
        secondary=source_message_data_association_table,
        back_populates="message_datas",
        default_factory=list,
    )


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

    def add_document(self, *, user: str, name: str, metadata: dict[str, Any]):
        document_data = DocumentData(
            id=self.make_id(),
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
                DocumentData.id == id & DocumentData.user_id == self._get_user_id(user)
            )
        ).scalar_one_or_none()

    def get_chats(self, user: str):
        return self._session.execute(
            select(ChatData).where(ChatData.user_id == self._get_user_id(user))
        )

    def add_chat(
        self,
        *,
        # This takes the ID instead of generating it itself, because we need to create
        # the Chat object before we add it to the database
        id: str,
        user: str,
        name: str,
        document_ids: list[str],
        source_storage_name: str,
        llm_name: str,
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
            source_storage_name=source_storage_name,
            llm_name=llm_name,
            params=params,
        )
        self._session.add(chat)
        self._session.commit()
        return chat

    def add_message(self, user: str, chat_id: str, content: str):
        chat_data = self._session.execute(
            select(ChatData).where(
                (ChatData.user_id == self._get_user_id(user)) & (ChatData.id == chat_id)
            )
        ).scalar_one_or_none()

        if chat_data is None:
            raise RagnaException

        message_data = MessageData(
            id=self.make_id(), chat_id=chat_data.id, content=content
        )
        chat_data.message_datas.append(message_data)
        self._session.commit()
