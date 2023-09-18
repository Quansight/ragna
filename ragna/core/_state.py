from __future__ import annotations

import functools
import re
from typing import Any, Optional

from sqlalchemy import Column, create_engine, ForeignKey, select, Table, types

from sqlalchemy.orm import DeclarativeBase, relationship, Session

from ragna.core import MessageRole, RagnaException, RagnaId, Source


class Id(types.TypeDecorator):
    impl = types.Uuid

    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return RagnaId.from_uuid(value)


class Base(DeclarativeBase):
    pass


# FIXME: Do we actually need this table? If we are sure that a user is unique and has to
#  be authenticated from the API layer, it seems having an extra mapping here is not
#  needed?
class UserData(Base):
    __tablename__ = "users"

    id = Column(Id, primary_key=True)
    name = Column(types.String)


document_chat_data_association_table = Table(
    "document_chat_data_association_table",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("chat_id", ForeignKey("chats.id"), primary_key=True),
)


# Name this state?
class DocumentData(Base):
    __tablename__ = "documents"

    id = Column(Id, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    name = Column(types.String)
    # Mind the trailing underscore here. Unfortunately, this is necessary, because
    # metadata without the underscore is reserved by SQLAlchemy
    metadata_ = Column(types.JSON)
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

    id = Column(Id, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    name = Column(types.String)
    document_datas = relationship(
        "DocumentData",
        secondary=document_chat_data_association_table,
        back_populates="chat_datas",
    )
    source_storage = Column(types.String)
    assistant = Column(types.String)
    params = Column(types.JSON)
    message_datas = relationship("MessageData", cascade="all, delete")
    started = Column(types.Boolean)
    closed = Column(types.Boolean)


source_message_data_association_table = Table(
    "source_message_data_association_table",
    Base.metadata,
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
    Column("message_id", ForeignKey("messages.id"), primary_key=True),
)


class SourceData(Base):
    __tablename__ = "sources"

    id = Column(Id, primary_key=True)

    document_id = Column(ForeignKey("documents.id"))
    document_data = relationship("DocumentData", back_populates="source_datas")

    location = Column(types.String)

    message_datas = relationship(
        "MessageData",
        secondary=source_message_data_association_table,
        back_populates="source_datas",
    )


class MessageData(Base):
    __tablename__ = "messages"

    id = Column(Id, primary_key=True)
    chat_id = Column(ForeignKey("chats.id"))
    content = Column(types.String)
    role = Column(types.Enum(MessageRole))
    source_id = Column(ForeignKey("sources.id"))
    source_datas = relationship(
        "SourceData",
        secondary=source_message_data_association_table,
        back_populates="message_datas",
    )


class State:
    def __init__(self, url: str):
        self._engine = create_engine(url)
        Base.metadata.create_all(self._engine)
        self._session = Session(self._engine)

    def __del__(self):
        if hasattr(self, "_session"):
            self._session.close()

    _UUID_STR_PATTERN = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )

    def is_id(self, obj: Any) -> bool:
        if not isinstance(obj, str):
            return False

        return self._UUID_STR_PATTERN.match(obj) is not None

    @functools.lru_cache(maxsize=1024)
    def _get_user_id(self, user: str):
        user_data = self._session.execute(
            select(UserData).where(UserData.name == user)
        ).scalar_one_or_none()
        if user_data is not None:
            return user_data.id

        user_data = UserData(id=RagnaId.make(), name=user)
        self._session.add(user_data)
        self._session.commit()
        return user_data.id

    def add_document(
        self, *, user: str, id: RagnaId, name: str, metadata: dict[str, Any]
    ):
        document_data = DocumentData(
            id=id,
            user_id=self._get_user_id(user),
            name=name,
            metadata_=metadata,
        )
        self._session.add(document_data)
        self._session.commit()
        return document_data

    def get_document(self, user: str, id: RagnaId) -> DocumentData:
        return self._session.execute(
            select(DocumentData).where(
                (DocumentData.user_id == self._get_user_id(user))
                & (DocumentData.id == id)
            )
        ).scalar_one_or_none()

    def get_chats(self, user: str):
        # FIXME: Add filters for started and closed here
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
        user: str,
        id: RagnaId,
        name: str,
        document_ids: list[RagnaId],
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

    def _get_chat(self, *, user: str, id: RagnaId):
        chat_data = self._session.execute(
            select(ChatData).where(
                (ChatData.id == id) & (ChatData.user_id == self._get_user_id(user))
            )
        ).scalar_one_or_none()
        if chat_data is None:
            raise RagnaException()
        return chat_data

    def start_chat(self, *, user: str, id: RagnaId):
        chat_data = self._get_chat(user=user, id=id)
        chat_data.started = True
        self._session.commit()

    def close_chat(self, *, user: str, id: RagnaId):
        chat_data = self._get_chat(user=user, id=id)
        chat_data.closed = True
        self._session.commit()

    def add_message(
        self,
        *,
        user: str,
        chat_id: RagnaId,
        id: RagnaId,
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
