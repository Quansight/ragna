from __future__ import annotations

import functools
import uuid

from sqlalchemy import Column, create_engine, ForeignKey, JSON, select, Table

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    MappedAsDataclass,
    relationship,
    Session,
)

from ._exceptions import RagnaException


class Base(MappedAsDataclass, DeclarativeBase):
    pass


def _make_id() -> str:
    return str(uuid.uuid4())


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
    metadata_: JSON
    chats: Mapped[list[ChatData]] = relationship(
        secondary=document_chat_data_association_table,
        back_populates="documents",
        default_factory=list,
    )


class ChatData(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    documents: Mapped[list[DocumentData]] = relationship(
        secondary=document_chat_data_association_table,
        back_populates="chats",
    )
    source_storage_name: Mapped[str]
    llm_name: Mapped[str]
    params: JSON
    messages: Mapped[list[MessageData]] = relationship(
        default_factory=list, cascade="all, delete"
    )


class MessageData(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(primary_key=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id"))
    content: Mapped[str]


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

    def add_document(self, *, user: str, name: str, metadata: JSON):
        document = DocumentData(
            id=_make_id(),
            user_id=self._get_user_id(user),
            name=name,
            metadata_=metadata,
        )
        self._session.add(document)
        self._session.commit()
        return document

    def get_document(self, id: str, user: str) -> DocumentData:
        return self._session.execute(
            select(DocumentData).where(
                DocumentData.id == id & DocumentData.user_id == self._get_user_id(user)
            )
        ).scalar_one_or_none()

    def add_chat(
        self,
        *,
        id: str,
        user: str,
        name: str,
        document_ids: list[str],
        source_storage_name: str,
        llm_name: str,
        params,
    ) -> ChatData:
        documents = (
            self._session.execute(
                select(DocumentData).where(DocumentData.id.in_(document_ids))
            )
            .scalars()
            .all()
        )
        if len(documents) != len(document_ids):
            raise RagnaException(
                set(document_ids) - {document.id for document in documents}
            )
        chat = ChatData(
            id=id,
            user_id=self._get_user_id(user),
            name=name,
            documents=documents,
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

        chat_data.messages.append(MessageData(chat_id=chat_data.id, content=content))
