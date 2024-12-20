from __future__ import annotations

import uuid
from typing import Any, Collection, Optional, cast
from urllib.parse import urlsplit

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from ragna.core import MetadataFilter, RagnaException

from . import _orm as orm
from . import _schemas as schemas


class UnknownUser(Exception):
    def __init__(
        self, name: Optional[str] = None, api_key: Optional[str] = None
    ) -> None:
        self.name = name
        self.api_key = api_key


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

    def _get_orm_user_by_name(self, session: Session, *, name: str) -> orm.User:
        user = cast(
            Optional[orm.User],
            session.execute(
                select(orm.User).where(orm.User.name == name)
            ).scalar_one_or_none(),
        )

        if user is None:
            raise UnknownUser(name)

        return user

    def maybe_add_user(self, session: Session, *, user: schemas.User) -> None:
        try:
            self._get_orm_user_by_name(session, name=user.name)
        except UnknownUser:
            orm_user = orm.User(id=uuid.uuid4(), name=user.name)
            session.add(orm_user)
            session.commit()

    def add_api_key(
        self, session: Session, *, user: str, api_key: schemas.ApiKey
    ) -> None:
        user_id = self._get_orm_user_by_name(session, name=user).id
        orm_api_key = orm.ApiKey(
            id=uuid.uuid4(),
            user_id=user_id,
            name=api_key.name,
            value=api_key.value,
            expires_at=api_key.expires_at,
        )
        session.add(orm_api_key)
        session.commit()

    def get_api_keys(self, session: Session, *, user: str) -> list[schemas.ApiKey]:
        return [
            self._to_schema.api_key(api_key)
            for api_key in session.execute(
                select(orm.ApiKey).where(
                    orm.ApiKey.user_id
                    == self._get_orm_user_by_name(session, name=user).id
                )
            )
            .scalars()
            .all()
        ]

    def delete_api_key(self, session: Session, *, user: str, id: uuid.UUID) -> None:
        orm_api_key = session.execute(
            select(orm.ApiKey).where(
                (orm.ApiKey.id == id)
                & (
                    orm.ApiKey.user_id
                    == self._get_orm_user_by_name(session, name=user).id
                )
            )
        ).scalar_one_or_none()

        if orm_api_key is None:
            raise RagnaException

        session.delete(orm_api_key)  # type: ignore[no-untyped-call]
        session.commit()

    def get_user_by_api_key(
        self, session: Session, api_key_value: str
    ) -> Optional[tuple[schemas.User, schemas.ApiKey]]:
        orm_api_key = session.execute(
            select(orm.ApiKey)  # type: ignore[attr-defined]
            .options(joinedload(orm.ApiKey.user))
            .where(orm.ApiKey.value == api_key_value)
        ).scalar_one_or_none()

        if orm_api_key is None:
            return None

        return (
            self._to_schema.user(orm_api_key.user),
            self._to_schema.api_key(orm_api_key),
        )

    def add_documents(
        self,
        session: Session,
        *,
        user: str,
        documents: list[schemas.Document],
    ) -> None:
        user_id = self._get_orm_user_by_name(session, name=user).id
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
        user_id = self._get_orm_user_by_name(session, name=user).id

        if chat.metadata_filter is not None:
            metadata_filter = orm.MetadataFilter(
                id=uuid.uuid4(),
                user_id=user_id,
                data=chat.metadata_filter.to_primitive(),
            )
            session.add(metadata_filter)
            session.commit()
            session.refresh(metadata_filter)
        else:
            metadata_filter = None

        if chat.documents is not None:
            document_ids = {document.id for document in chat.documents}
            documents = (
                session.execute(
                    select(orm.Document).where(orm.Document.id.in_(document_ids))
                )
                .scalars()
                .all()
            )
            if len(documents) != len(document_ids):
                raise RagnaException(
                    str(set(document_ids) - {document.id for document in documents})
                )
        else:
            documents = []

        session.add(
            orm.Chat(
                id=chat.id,
                user_id=user_id,
                name=chat.name,
                metadata_filter=metadata_filter,
                documents=documents,
                source_storage=chat.source_storage,
                assistant=chat.assistant,
                corpus_name=chat.corpus_name,
                params=chat.params,
                prepared=chat.prepared,
            )
        )
        session.commit()

    def _select_chat(self, *, eager: bool = False) -> Any:
        selector = select(orm.Chat)
        if eager:
            selector = selector.options(  # type: ignore[attr-defined]
                joinedload(orm.Chat.messages)
                .joinedload(orm.Message.sources)
                .joinedload(orm.Source.document),
                joinedload(orm.Chat.documents),
            )
        return selector

    def get_chats(self, session: Session, *, user: str) -> list[schemas.Chat]:
        return [
            self._to_schema.chat(chat)
            for chat in session.execute(
                self._select_chat(eager=True).where(
                    orm.Chat.user_id
                    == self._get_orm_user_by_name(session, name=user).id
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
                    & (
                        orm.Chat.user_id
                        == self._get_orm_user_by_name(session, name=user).id
                    )
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
        user_id = self._get_orm_user_by_name(session, name=user).id

        # We need to load the metadata filter here, because it only has an ID inside the
        # DB and thus cannot be retrieved by the converter
        if chat.metadata_filter is not None:
            clause = select(orm.MetadataFilter).where(
                (orm.MetadataFilter.user_id == user_id)
                & (orm.MetadataFilter.chat_id == chat.id)
            )
            orm_metadata_filter = session.execute(clause).scalar_one()
        else:
            orm_metadata_filter = None

        orm_chat = self._to_orm.chat(
            chat, user_id=user_id, orm_metadata_filter=orm_metadata_filter
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
            document_id=source.document_id,
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
        orm_metadata_filter: orm.MetadataFilter | None,
    ) -> orm.Chat:
        if chat.documents is not None:
            documents = [
                self.document(document, user_id=user_id) for document in chat.documents
            ]
        else:
            documents = []

        return orm.Chat(
            id=chat.id,
            user_id=user_id,
            name=chat.name,
            documents=documents,
            metadata_filter=orm_metadata_filter,
            source_storage=chat.source_storage,
            assistant=chat.assistant,
            params=chat.params,
            messages=[
                self.message(message, chat_id=chat.id) for message in chat.messages
            ],
            prepared=chat.prepared,
        )


class OrmToSchemaConverter:
    def user(self, user: orm.User) -> schemas.User:
        return schemas.User(name=user.name)

    def api_key(self, api_key: orm.ApiKey) -> schemas.ApiKey:
        return schemas.ApiKey(
            id=api_key.id,
            name=api_key.name,
            expires_at=api_key.expires_at,
            obfuscated=True,
            value=api_key.value,
        )

    def document(self, document: orm.Document) -> schemas.Document:
        return schemas.Document(
            id=document.id, name=document.name, metadata=document.metadata_
        )

    def source(self, source: orm.Source) -> schemas.Source:
        return schemas.Source(
            id=source.id,
            document_id=(document := self.document(source.document)).id,
            document_name=document.name,
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
        if chat.metadata_filter is not None:
            metadata_filter = MetadataFilter.from_primitive(chat.metadata_filter.data)
            documents = None
        elif chat.documents:
            metadata_filter = None
            documents = [self.document(document) for document in chat.documents]
        else:
            metadata_filter = None
            documents = None

        return schemas.Chat(
            id=chat.id,
            name=chat.name,
            metadata_filter=metadata_filter,
            documents=documents,
            source_storage=chat.source_storage,
            assistant=chat.assistant,
            corpus_name=chat.corpus_name,
            params=chat.params,
            messages=[self.message(message) for message in chat.messages],
            prepared=chat.prepared,
        )
