import asyncio
import uuid

import aiofiles
from fastapi import UploadFile

import ragna.core

from ._database import Database


class Engine:
    def __init__(self, config):
        self._config = config
        self._database = Database(config)

    async def _upload_document(self, document: UploadFile):
        id = uuid.uuid4()
        async with aiofiles.open(f"/tmp/{id}", "wb") as file:
            while content := await document.read(1024):
                await file.write(content)

        return id

    async def upload_documents(self, documents: list[UploadFile]):
        ids = await asyncio.gather(
            *[self._upload_document(document) for document in documents]
        )
        print(ids)

    async def create_chat(self) -> None:
        pass

    async def get_chats(self, *, user: str) -> list[ragna.core.Chat]:
        with self._database.session() as session:
            return self._database.get_chats(session, user=user)

    async def get_chat(self, *, user: str, chat_id: uuid.UUID) -> ragna.core.Chat:
        with self._database.session() as session:
            return self._database.get_chat(session, user=user, id=chat_id)

    async def prepare_chat(
        self, *, user: str, chat_id: uuid.UUID
    ) -> ragna.core.Message:
        chat = await self.get_chat(user=user, chat_id=chat_id)
        return await chat.prepare()

    async def answer_prompt(
        self, *, user: str, chat_id: uuid.UUID, prompt: str
    ) -> ragna.core.Message:
        chat = await self.get_chat(user=user, chat_id=chat_id)
        return await chat.answer(prompt, stream=True)

    async def delete_chat(self, *, user: str, chat_id: uuid.UUID) -> None:
        pass
