import asyncio
import uuid

import aiofiles
from fastapi import UploadFile


class Engine:
    def __init__(self, config):
        self.config = config

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
