from sqlalchemy import Column, ForeignKey, Table, types
from sqlalchemy.orm import DeclarativeBase, relationship

from ragna.core import MessageRole, RagnaId


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
