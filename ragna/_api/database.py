from __future__ import annotations

import functools
import uuid
from typing import Any, Callable, Optional, cast
from urllib.parse import urlsplit

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker as _sessionmaker

from ragna.core import RagnaException

from . import orm, schemas


def get_sessionmaker(database_url: str) -> Callable[[], Session]:
    components = urlsplit(database_url)
    if components.scheme == "sqlite":
        connect_args = dict(check_same_thread=False)
    else:
        connect_args = dict()
    engine = create_engine(database_url, connect_args=connect_args)
    orm.Base.metadata.create_all(bind=engine)
    return _sessionmaker(autocommit=False, autoflush=False, bind=engine)


@functools.lru_cache(maxsize=1024)
def _get_user_id(session: Session, username: str) -> uuid.UUID:
    user: Optional[orm.User] = session.execute(
        select(orm.User).where(orm.User.name == username)
    ).scalar_one_or_none()

    if user is None:
        # Add a new user if the current username is not registered yet. Since this is
        # behind the authentication layer, we don't need any extra security here.
        user = orm.User(id=uuid.uuid4(), name=username)
        session.add(user)
        session.commit()

    return cast(uuid.UUID, user.id)


def add_document(
    session: Session, *, user: str, document: schemas.Document, metadata: dict[str, Any]
) -> None:
    session.add(
        orm.Document(
            id=document.id,
            user_id=_get_user_id(session, user),
            name=document.name,
            metadata_=metadata,
        )
    )
    session.commit()


def _orm_to_schema_document(document: orm.Document) -> schemas.Document:
    return schemas.Document(id=document.id, name=document.name)


@functools.lru_cache(maxsize=1024)
def get_document(
    session: Session, *, user: str, id: uuid.UUID
) -> tuple[schemas.Document, dict[str, Any]]:
    document = session.execute(
        select(orm.Document).where(
            (orm.Document.user_id == _get_user_id(session, user))
            & (orm.Document.id == id)
        )
    ).scalar_one_or_none()
    return _orm_to_schema_document(document), document.metadata_


def add_chat(session: Session, *, user: str, chat: schemas.Chat) -> None:
    document_ids = {document.id for document in chat.metadata.documents}
    documents = (
        session.execute(select(orm.Document).where(orm.Document.id.in_(document_ids)))
        .scalars()
        .all()
    )
    if len(documents) != len(document_ids):
        raise RagnaException(
            str(set(document_ids) - {document.id for document in documents})
        )
    session.add(
        orm.Chat(
            id=chat.id,
            user_id=_get_user_id(session, user),
            name=chat.metadata.name,
            documents=documents,
            source_storage=chat.metadata.source_storage,
            assistant=chat.metadata.assistant,
            params=chat.metadata.params,
            prepared=chat.prepared,
        )
    )
    session.commit()


def _orm_to_schema_chat(chat: orm.Chat) -> schemas.Chat:
    documents = [
        schemas.Document(id=document.id, name=document.name)
        for document in chat.documents
    ]
    messages = [
        schemas.Message(
            id=message.id,
            role=message.role,
            content=message.content,
            sources=[
                schemas.Source(
                    id=source.id,
                    document=_orm_to_schema_document(source.document),
                    location=source.location,
                )
                for source in message.sources
            ],
            timestamp=message.timestamp,
        )
        for message in chat.messages
    ]
    return schemas.Chat(
        id=chat.id,
        metadata=schemas.ChatMetadata(
            name=chat.name,
            documents=documents,
            source_storage=chat.source_storage,
            assistant=chat.assistant,
            params=chat.params,  # type: ignore[arg-type]
        ),
        messages=messages,
        prepared=chat.prepared,
    )


def get_chats(session: Session, *, user: str) -> list[schemas.Chat]:
    return [
        _orm_to_schema_chat(chat)
        for chat in session.execute(
            select(orm.Chat).where(orm.Chat.user_id == _get_user_id(session, user))
        )
        .scalars()
        .all()
    ]


def _get_orm_chat(session: Session, *, user: str, id: uuid.UUID) -> orm.Chat:
    chat: Optional[orm.Chat] = session.execute(
        select(orm.Chat).where(
            (orm.Chat.id == id) & (orm.Chat.user_id == _get_user_id(session, user))
        )
    ).scalar_one_or_none()
    if chat is None:
        raise RagnaException()
    return chat


def get_chat(session: Session, *, user: str, id: uuid.UUID) -> schemas.Chat:
    return _orm_to_schema_chat(_get_orm_chat(session, user=user, id=id))


def _schema_to_orm_source(session: Session, source: schemas.Source) -> orm.Source:
    orm_source: Optional[orm.Source] = session.execute(
        select(orm.Source).where(orm.Source.id == source.id)
    ).scalar_one_or_none()

    if orm_source is None:
        orm_source = orm.Source(
            id=source.id,
            document_id=source.document.id,
            location=source.location,
        )
        session.add(orm_source)
        session.commit()
        session.refresh(orm_source)

    return orm_source


def _schema_to_orm_message(
    session: Session, chat_id: uuid.UUID, message: schemas.Message
) -> orm.Message:
    orm_message: Optional[orm.Message] = session.execute(
        select(orm.Message).where(orm.Message.id == message.id)
    ).scalar_one_or_none()
    if orm_message is None:
        orm_message = orm.Message(
            id=message.id,
            chat_id=chat_id,
            content=message.content,
            role=message.role,
            sources=[
                _schema_to_orm_source(session, source=source)
                for source in message.sources
            ],
            timestamp=message.timestamp,
        )
        session.add(orm_message)
        session.commit()
        session.refresh(orm_message)

    return orm_message


def update_chat(session: Session, user: str, chat: schemas.Chat) -> None:
    orm_chat = _get_orm_chat(session, user=user, id=chat.id)

    orm_chat.prepared = chat.prepared
    orm_chat.messages = [
        _schema_to_orm_message(session, chat_id=chat.id, message=message)
        for message in chat.messages
    ]

    session.commit()


def delete_chat(session: Session, user: str, id: uuid.UUID) -> None:
    orm_chat = _get_orm_chat(session, user=user, id=id)
    session.delete(orm_chat)  # type: ignore[no-untyped-call]
    session.commit()
