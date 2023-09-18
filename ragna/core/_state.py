from __future__ import annotations

import functools
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
class UserState(Base):
    __tablename__ = "users"

    id = Column(Id, primary_key=True)
    name = Column(types.String)


document_chat_state_association_table = Table(
    "document_chat_state_association_table",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("chat_id", ForeignKey("chats.id"), primary_key=True),
)


class DocumentState(Base):
    __tablename__ = "documents"

    id = Column(Id, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    name = Column(types.String)
    # Mind the trailing underscore here. Unfortunately, this is necessary, because
    # metadata without the underscore is reserved by SQLAlchemy
    metadata_ = Column(types.JSON)
    chat_states = relationship(
        "ChatState",
        secondary=document_chat_state_association_table,
        back_populates="document_states",
    )
    source_states = relationship(
        "SourceState",
        back_populates="document_state",
    )


class ChatState(Base):
    __tablename__ = "chats"

    id = Column(Id, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    name = Column(types.String)
    document_states = relationship(
        "DocumentState",
        secondary=document_chat_state_association_table,
        back_populates="chat_states",
    )
    source_storage = Column(types.String)
    assistant = Column(types.String)
    params = Column(types.JSON)
    message_states = relationship("MessageState")
    started = Column(types.Boolean)
    closed = Column(types.Boolean)


source_message_state_association_table = Table(
    "source_message_state_association_table",
    Base.metadata,
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
    Column("message_id", ForeignKey("messages.id"), primary_key=True),
)


class SourceState(Base):
    __tablename__ = "sources"

    id = Column(Id, primary_key=True)

    document_id = Column(ForeignKey("documents.id"))
    document_state = relationship("DocumentState", back_populates="source_states")

    location = Column(types.String)

    message_states = relationship(
        "MessageState",
        secondary=source_message_state_association_table,
        back_populates="source_states",
    )


class MessageState(Base):
    __tablename__ = "messages"

    id = Column(Id, primary_key=True)
    chat_id = Column(ForeignKey("chats.id"))
    content = Column(types.String)
    role = Column(types.Enum(MessageRole))
    source_id = Column(ForeignKey("sources.id"))
    source_states = relationship(
        "SourceState",
        secondary=source_message_state_association_table,
        back_populates="message_states",
    )


class State:
    def __init__(self, url: str):
        self._engine = create_engine(url)
        Base.metadata.create_all(self._engine)
        self._session = Session(self._engine)

    def __del__(self):
        if hasattr(self, "_session"):
            self._session.close()

    @functools.lru_cache(maxsize=1024)
    def _get_user_id(self, user: str):
        user_state = self._session.execute(
            select(UserState).where(UserState.name == user)
        ).scalar_one_or_none()
        if user_state is not None:
            return user_state.id

        user_state = UserState(id=RagnaId.make(), name=user)
        self._session.add(user_state)
        self._session.commit()
        return user_state.id

    def add_document(
        self, *, user: str, id: RagnaId, name: str, metadata: dict[str, Any]
    ):
        document_state = DocumentState(
            id=id,
            user_id=self._get_user_id(user),
            name=name,
            metadata_=metadata,
        )
        self._session.add(document_state)
        self._session.commit()
        return document_state

    @functools.lru_cache(maxsize=1024)
    def get_document(self, user: str, id: RagnaId) -> DocumentState:
        return self._session.execute(
            select(DocumentState).where(
                (DocumentState.user_id == self._get_user_id(user))
                & (DocumentState.id == id)
            )
        ).scalar_one_or_none()

    def get_chats(self, user: str):
        # FIXME: Add filters for started and closed here
        return (
            self._session.execute(
                select(ChatState).where(ChatState.user_id == self._get_user_id(user))
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
    ) -> ChatState:
        document_states = (
            self._session.execute(
                select(DocumentState).where(DocumentState.id.in_(document_ids))
            )
            .scalars()
            .all()
        )
        if len(document_states) != len(document_ids):
            raise RagnaException(
                set(document_ids) - {document.id for document in document_states}
            )
        chat = ChatState(
            id=id,
            user_id=self._get_user_id(user),
            name=name,
            document_states=document_states,
            source_storage=source_storage,
            assistant=assistant,
            params=params,
            started=False,
            closed=False,
        )
        self._session.add(chat)
        self._session.commit()
        return chat

    def get_chat(self, *, user: str, id: RagnaId):
        chat_state = self._session.execute(
            select(ChatState).where(
                (ChatState.id == id) & (ChatState.user_id == self._get_user_id(user))
            )
        ).scalar_one_or_none()
        if chat_state is None:
            raise RagnaException()
        return chat_state

    def start_chat(self, *, user: str, id: RagnaId):
        chat_state = self.get_chat(user=user, id=id)
        chat_state.started = True
        self._session.commit()

    def close_chat(self, *, user: str, id: RagnaId):
        chat_state = self.get_chat(user=user, id=id)
        chat_state.closed = True
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
        chat_state = self._session.execute(
            select(ChatState).where(
                (ChatState.user_id == self._get_user_id(user))
                & (ChatState.id == chat_id)
            )
        ).scalar_one_or_none()
        if chat_state is None:
            raise RagnaException

        if sources is not None:
            sources = {s.id: s for s in sources}
            source_states = list(
                self._session.execute(
                    select(SourceState).where(SourceState.id.in_(sources.keys()))
                )
                .scalars()
                .all()
            )
            missing_source_ids = sources.keys() - {state.id for state in source_states}
            if missing_source_ids:
                for id in missing_source_ids:
                    source = sources[id]
                    source_state = SourceState(
                        id=RagnaId.make(),
                        document_id=source.document_id,
                        document_state=self.get_document(
                            user=user, id=source.document_id
                        ),
                        location=source.location,
                    )
                    self._session.add(source_state)
                    source_states.append(source_state)
        else:
            source_states = []

        message_state = MessageState(
            id=id,
            chat_id=chat_state.id,
            content=content,
            role=role,
            source_states=source_states,
        )
        self._session.add(message_state)

        chat_state.message_states.append(message_state)

        self._session.commit()
