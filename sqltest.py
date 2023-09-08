from __future__ import annotations

from pathlib import Path

from sqlalchemy import Column, create_engine, ForeignKey, select, Table

from sqlalchemy.orm import Mapped, mapped_column, registry, relationship, Session

Path("test.db").unlink()

import functools


reg = registry()
Base = reg.generate_base()


@reg.mapped_as_dataclass
class User:
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str]


document_conversation_association_table = Table(
    "document_conversation_association_table",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("conversation_id", ForeignKey("conversations.id"), primary_key=True),
)


# each document needs to have user assoicated with it
@reg.mapped_as_dataclass
class Document:
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str]
    location: Mapped[str]
    conversations: Mapped[list[Conversation]] = relationship(
        secondary=document_conversation_association_table,
        back_populates="documents",
        default_factory=list,
    )


@reg.mapped_as_dataclass
class Conversation:
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    documents: Mapped[list[Document]] = relationship(
        secondary=document_conversation_association_table,
        back_populates="conversations",
    )
    # config: Mapped[JSON] = mapped_column(default={})
    messages: Mapped[list[Message]] = relationship(
        default_factory=list, cascade="all, delete"
    )


@reg.mapped_as_dataclass
class Message:
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    content: Mapped[str]
    # config: Mapped[JSON] = mapped_column(default={})


engine = create_engine("sqlite:///test.db", echo=False)
Base.metadata.create_all(engine)


class RagnaException(Exception):
    pass


# are sessions cheap?
# do they commit automatically?
with Session(engine) as session:

    @functools.lru_cache()
    def _get_user_id(username: str):
        user_id = session.execute(
            select(User.id).where(User.name == username)
        ).scalar_one_or_none()
        if user_id is not None:
            return user_id

        user = User(name=username)
        session.add(user)
        session.commit()

        return user.id

    def add_document(name: str, location: str):
        document = Document(name=name, location=location)
        session.add(document)
        session.commit()
        return document

    def start_conversation(username: str, name: str, documents):
        conversation = Conversation(
            user_id=_get_user_id(username), name=name, documents=documents
        )
        session.add(conversation)
        session.commit()
        return conversation

    def delete_conversation(username, name):
        conversation = session.execute(
            select(Conversation).where(
                (Conversation.user_id == _get_user_id(username))
                & (Conversation.name == name)
            )
        ).scalar_one_or_none()

        if conversation is None:
            raise RagnaException

        session.delete(conversation)
        session.commit()

    def get_conversations(username: str):
        return session.execute(
            select(Conversation).where(Conversation.user_id == _get_user_id(username))
        ).all()

    def change_conversation_name(username: str, old_name: str, new_name: str):
        conversation = session.execute(
            select(Conversation).where(
                (Conversation.user_id == _get_user_id(username))
                & (Conversation.name == old_name)
            )
        ).scalar_one_or_none()

        if conversation is None:
            raise RagnaException

        conversation.name = new_name
        session.commit()

        return conversation

    def answer(username: str, conversation_name: str, prompt: str):
        conversation = session.execute(
            select(Conversation).where(
                (Conversation.user_id == _get_user_id(username))
                & (Conversation.name == conversation_name)
            )
        ).scalar_one_or_none()

        if conversation is None:
            raise RagnaException

        answer = f"Fake answer to the user question '{prompt}'"

        conversation.messages.extend(
            [
                Message(conversation_id=conversation.id, content=prompt),
                Message(conversation_id=conversation.id, content=answer),
            ]
        )
        session.commit()

        return answer

    foo = add_document("foo.pdf", "/here/foo.pdf")
    bar = add_document("bar.pdf", "/here/bar.pdf")
    baz = add_document("baz.pdf", "/here/baz.pdf")

    print(
        start_conversation("pmeier", name="philips first convo", documents=[foo, bar])
    )
    print(start_conversation("pmeier", name="philips second convo", documents=[bar]))
    print(
        start_conversation(
            "costrouchov", name="chris' first convo", documents=[baz, bar]
        )
    )

    print(get_conversations("alewis"))
    print(get_conversations("pmeier"))

    print(
        change_conversation_name(
            "pmeier", "philips first convo", "philips changed convo"
        )
    )
    print(get_conversations("pmeier"))

    print(answer("pmeier", "philips changed convo", "Huh?"))
    print(get_conversations("pmeier"))

    delete_conversation("pmeier", "philips changed convo")
    print(get_conversations("pmeier"))
