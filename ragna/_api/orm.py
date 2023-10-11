from sqlalchemy import Column, ForeignKey, Table, types
from sqlalchemy.orm import DeclarativeBase, relationship

from ragna.core import MessageRole


class Base(DeclarativeBase):
    pass


# FIXME: Do we actually need this table? If we are sure that a user is unique and has to
#  be authenticated from the API layer, it seems having an extra mapping here is not
#  needed?
class User(Base):
    __tablename__ = "users"

    id = Column(types.UUID, primary_key=True)
    name = Column(types.String)


document_chat_association_table = Table(
    "document_chat_association_table",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("chat_id", ForeignKey("chats.id"), primary_key=True),
)


class Document(Base):
    __tablename__ = "documents"

    id = Column(types.UUID, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    name = Column(types.String)
    # Mind the trailing underscore here. Unfortunately, this is necessary, because
    # metadata without the underscore is reserved by SQLAlchemy
    metadata_ = Column(types.JSON)
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

    id = Column(types.UUID, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    name = Column(types.String)
    documents = relationship(
        "Document",
        secondary=document_chat_association_table,
        back_populates="chats",
    )
    source_storage = Column(types.String)
    assistant = Column(types.String)
    params = Column(types.JSON)
    messages = relationship("Message")
    prepared = Column(types.Boolean)


source_message_association_table = Table(
    "source_message_association_table",
    Base.metadata,
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
    Column("message_id", ForeignKey("messages.id"), primary_key=True),
)


class Source(Base):
    __tablename__ = "sources"

    id = Column(types.UUID, primary_key=True)

    document_id = Column(ForeignKey("documents.id"))
    document = relationship("Document", back_populates="sources")

    location = Column(types.String)

    messages = relationship(
        "Message",
        secondary=source_message_association_table,
        back_populates="sources",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(types.UUID, primary_key=True)
    chat_id = Column(ForeignKey("chats.id"))
    content = Column(types.String)
    role = Column(types.Enum(MessageRole))
    source_id = Column(ForeignKey("sources.id"))
    sources = relationship(
        "Source",
        secondary=source_message_association_table,
        back_populates="messages",
    )
    timestamp = Column(types.DATETIME)
