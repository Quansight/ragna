from __future__ import annotations

import uuid
from typing import Any, Collection, Optional
from urllib.parse import urlsplit

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from ragna.core import RagnaException

from . import _orm as orm
from . import _schemas as schemas


class Database:
    def __init__(self, url: str) -> None:
        components = urlsplit(url)
        if components.scheme == "sqlite":
            connect_args = dict(check_same_thread=False)
        else:
            connect_args = dict()
        engine = create_engine(url, connect_args=connect_args)
        orm.Base.metadata.create_all(bind=engine)

        self.get_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        self._to_orm = SchemaToOrmConverter()
        self._to_schema = OrmToSchemaConverter()

    def _get_user(self, session: Session, *, username: str) -> orm.User:
        user: Optional[orm.User] = session.execute(
            select(orm.User).where(orm.User.name == username)
        ).scalar_one_or_none()

        if user is None:
            # Add a new user if the current username is not registered yet. Since this
            # is behind the authentication layer, we don't need any extra security here.
            user = orm.User(id=uuid.uuid4(), name=username)
            session.add(user)
            session.commit()

        return user

    def add_documents(
        self,
        session: Session,
        *,
        user: str,
        documents: list[schemas.Document],
    ) -> None:
        user_id = self._get_user(session, username=user).id
        session.add_all(
            [self._to_orm.document(document, user_id=user_id) for document in documents]
        )
        session.commit()

    def _get_orm_documents(
        self, session: Session, *, user: str, ids: Collection[uuid.UUID]
    ) -> list[orm.Document]:
        # FIXME also check if the user is allowed to access the documents
        # FIXME: maybe just take the user id to avoid getting it twice in add_chat?
        documents = (
            session.execute(select(orm.Document).where(orm.Document.id.in_(ids)))
            .scalars()
            .all()
        )
        if len(documents) != len(ids):
            raise RagnaException(
                str(set(ids) - {document.id for document in documents})
            )

        return documents  # type: ignore[no-any-return]

    def get_documents(
        self, session: Session, *, user: str, ids: Collection[uuid.UUID]
    ) -> list[schemas.Document]:
        return [
            self._to_schema.document(document)
            for document in self._get_orm_documents(session, user=user, ids=ids)
        ]

    def add_chat(self, session: Session, *, user: str, chat: schemas.Chat) -> None:
        orm_chat = self._to_orm.chat(
            chat, user_id=self._get_user(session, username=user).id
        )
        # We need to merge and not add here, because the documents are already in the DB
        session.merge(orm_chat)
        session.commit()

    def _select_chat(self, *, eager: bool = False) -> Any:
        selector = select(orm.Chat)
        if eager:
            selector = selector.options(  # type: ignore[attr-defined]
                joinedload(orm.Chat.messages).joinedload(orm.Message.sources),
                joinedload(orm.Chat.documents),
            )
        return selector

    def get_chats(self, session: Session, *, user: str) -> list[schemas.Chat]:
        return [
            self._to_schema.chat(chat)
            for chat in session.execute(
                self._select_chat(eager=True).where(
                    orm.Chat.user_id == self._get_user(session, username=user).id
                )
            )
            .scalars()
            .unique()
            .all()
        ]

    def _get_orm_chat(
        self, session: Session, *, user: str, id: uuid.UUID, eager: bool = False
    ) -> orm.Chat:
        chat: Optional[orm.Chat] = (
            session.execute(
                self._select_chat(eager=eager).where(
                    (orm.Chat.id == id)
                    & (orm.Chat.user_id == self._get_user(session, username=user).id)
                )
            )
            .unique()
            .scalar_one_or_none()
        )
        if chat is None:
            raise RagnaException()
        return chat

    def get_chat(self, session: Session, *, user: str, id: uuid.UUID) -> schemas.Chat:
        return self._to_schema.chat(
            (self._get_orm_chat(session, user=user, id=id, eager=True))
        )

    def update_chat(self, session: Session, user: str, chat: schemas.Chat) -> None:
        orm_chat = self._to_orm.chat(
            chat, user_id=self._get_user(session, username=user).id
        )
        session.merge(orm_chat)
        session.commit()

    def delete_chat(self, session: Session, user: str, id: uuid.UUID) -> None:
        orm_chat = self._get_orm_chat(session, user=user, id=id)
        session.delete(orm_chat)  # type: ignore[no-untyped-call]
        session.commit()


class SchemaToOrmConverter:
    def document(
        self, document: schemas.Document, *, user_id: uuid.UUID
    ) -> orm.Document:
        return orm.Document(
            id=document.id,
            user_id=user_id,
            name=document.name,
            metadata_=document.metadata,
        )

    def source(self, source: schemas.Source) -> orm.Source:
        return orm.Source(
            id=source.id,
            document_id=source.document.id,
            location=source.location,
            content=source.content,
            num_tokens=source.num_tokens,
        )

    def message(self, message: schemas.Message, *, chat_id: uuid.UUID) -> orm.Message:
        return orm.Message(
            id=message.id,
            chat_id=chat_id,
            content=message.content,
            role=message.role,
            sources=[self.source(source) for source in message.sources],
            timestamp=message.timestamp,
        )

    def chat(
        self,
        chat: schemas.Chat,
        *,
        user_id: uuid.UUID,
    ) -> orm.Chat:
        return orm.Chat(
            id=chat.id,
            user_id=user_id,
            name=chat.name,
            documents=[
                self.document(document, user_id=user_id) for document in chat.documents
            ],
            source_storage=chat.source_storage,
            assistant=chat.assistant,
            params=chat.params,
            messages=[
                self.message(message, chat_id=chat.id) for message in chat.messages
            ],
            prepared=chat.prepared,
        )


class OrmToSchemaConverter:
    def document(self, document: orm.Document) -> schemas.Document:
        return schemas.Document(
            id=document.id, name=document.name, metadata=document.metadata_
        )

    def source(self, source: orm.Source) -> schemas.Source:
        return schemas.Source(
            id=source.id,
            document=self.document(source.document),
            location=source.location,
            content=source.content,
            num_tokens=source.num_tokens,
        )

    def message(self, message: orm.Message) -> schemas.Message:
        return schemas.Message(
            id=message.id,
            role=message.role,  # type: ignore[arg-type]
            content=message.content,
            sources=[self.source(source) for source in message.sources],
            timestamp=message.timestamp,
        )

    def chat(self, chat: orm.Chat) -> schemas.Chat:
        return schemas.Chat(
            id=chat.id,
            name=chat.name,
            documents=[self.document(document) for document in chat.documents],
            source_storage=chat.source_storage,
            assistant=chat.assistant,
            params=chat.params,
            messages=[self.message(message) for message in chat.messages],
            prepared=chat.prepared,
        )
