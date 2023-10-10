from __future__ import annotations

import functools
from typing import Any, Callable

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker as _sessionmaker

from ragna.core import Message, RagnaException, RagnaId

from . import orm, schemas


def get_sessionmaker(database_url: str) -> Callable[[], Session]:
    engine = create_engine(database_url)
    orm.Base.metadata.create_all(bind=engine)
    return _sessionmaker(autocommit=False, autoflush=False, bind=engine)


@functools.lru_cache(maxsize=1024)
def _get_user_id(session: Session, username: str) -> RagnaId:
    user = session.execute(
        select(orm.User).where(orm.User.name == username)
    ).scalar_one_or_none()

    if user is None:
        # Add a new user if the current username is not registered yet. Since this is
        # behind the authentication layer, we don't need any extra security here.
        user = orm.User(id=RagnaId.make(), name=username)
        session.add(user)
        session.commit()

    return user.id


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
    session: Session, *, user: str, id: RagnaId
) -> tuple[schemas.Document, dict[str, Any]]:
    document = session.execute(
        select(orm.Document).where(
            (orm.Document.user_id == _get_user_id(session, user))
            & (orm.Document.id == id)
        )
    ).scalar_one_or_none()
    return _orm_to_schema_document(document), document.metadata


def add_chat(session: Session, *, user: str, chat: schemas.Chat):
    document_ids = {document.id for document in chat.metadata.documents}
    documents = (
        session.execute(select(orm.Document).where(orm.Document.id.in_(document_ids)))
        .scalars()
        .all()
    )
    if len(documents) != len(document_ids):
        raise RagnaException(
            set(document_ids) - {document.id for document in documents}
        )
    session.add(
        orm.Chat(
            id=chat.id,
            user_id=_get_user_id(session, user),
            name=chat.metadata.name,
            document_states=documents,
            source_storage=chat.metadata.source_storage,
            assistant=chat.metadata.assistant,
            params=chat.metadata.params,
            started=chat.started,
            closed=chat.started,
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
            params=chat.params,
        ),
        messages=messages,
        started=chat.started,
        closed=chat.closed,
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


def _get_orm_chat(session: Session, *, user: str, id: RagnaId) -> orm.Chat:
    chat = session.execute(
        select(orm.Chat).where(
            (orm.Chat.id == id) & (orm.Chat.user_id == _get_user_id(session, user))
        )
    ).scalar_one_or_none()
    if chat is None:
        raise RagnaException()
    return chat


def get_chat(session: Session, *, user: str, id: RagnaId) -> schemas.Chat:
    return _orm_to_schema_chat(_get_orm_chat(session, user=user, id=id))


def start_chat(session: Session, *, user: str, id: RagnaId) -> schemas.Chat:
    chat = _get_orm_chat(session, user=user, id=id)
    chat.started = True
    session.commit()
    session.refresh(chat)
    return _orm_to_schema_chat(chat)


def close_chat(session: Session, *, user: str, id: RagnaId) -> schemas.Chat:
    chat = _get_orm_chat(session, user=user, id=id)
    chat.closed = True
    session.commit()
    session.refresh(chat)
    return _orm_to_schema_chat(chat)


def add_message(
    session: Session,
    message: Message,
    *,
    user: str,
    chat_id: RagnaId,
):
    chat_state = session.execute(
        select(orm.Chat).where(
            (orm.Chat.user_id == _get_user_id(session, user)) & (orm.Chat.id == chat_id)
        )
    ).scalar_one_or_none()
    if chat_state is None:
        raise RagnaException

    if message.sources is not None:
        sources = {s.id: s for s in message.sources}
        source_states = list(
            session.execute(select(orm.Source).where(orm.Source.id.in_(sources.keys())))
            .scalars()
            .all()
        )
        missing_source_ids = sources.keys() - {state.id for state in source_states}
        if missing_source_ids:
            for id in missing_source_ids:
                source = sources[id]
                source_state = orm.Source(
                    id=RagnaId.make(),
                    document_id=source.document_id,
                    document_state=self.get_document(user=user, id=source.document_id),
                    location=source.location,
                )
                session.add(source_state)
                source_states.append(source_state)
    else:
        source_states = []

    message_state = orm.Message(
        id=message.id,
        chat_id=chat_state.id,
        content=message.content,
        role=message.role,
        source_states=source_states,
        timestamp=message.timestamp,
    )
    session.add(message_state)

    chat_state.message_states.append(message_state)

    session.commit()
