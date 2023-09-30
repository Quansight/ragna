from __future__ import annotations

import functools
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ragna.core import Message, RagnaException, RagnaId

from ._orm import Base, ChatState, DocumentState, MessageState, SourceState, UserState


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
        message: Message,
        *,
        user: str,
        chat_id: RagnaId,
    ):
        chat_state = self._session.execute(
            select(ChatState).where(
                (ChatState.user_id == self._get_user_id(user))
                & (ChatState.id == chat_id)
            )
        ).scalar_one_or_none()
        if chat_state is None:
            raise RagnaException

        if message.sources is not None:
            sources = {s.id: s for s in message.sources}
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
            id=message.id,
            chat_id=chat_state.id,
            content=message.content,
            role=message.role,
            source_states=source_states,
            timestamp=message.timestamp,
        )
        self._session.add(message_state)

        chat_state.message_states.append(message_state)

        self._session.commit()
