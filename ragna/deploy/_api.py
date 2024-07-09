import uuid
from typing import Annotated, AsyncIterator

import pydantic
from fastapi import (
    APIRouter,
    Body,
    Depends,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from ragna._compat import anext
from ragna.core._utils import default_user

from . import _schemas as schemas
from ._engine import Engine


def make_router(engine: Engine) -> APIRouter:
    router = APIRouter(tags=["API"])

    def get_user() -> str:
        return default_user()

    UserDependency = Annotated[str, Depends(get_user)]

    @router.post("/documents")
    def register_documents(
        user: UserDependency, document_registrations: list[schemas.DocumentRegistration]
    ) -> list[schemas.Document]:
        return engine.register_documents(
            user=user, document_registrations=document_registrations
        )

    @router.put("/documents")
    async def upload_documents(
        user: UserDependency, documents: list[UploadFile]
    ) -> None:
        def make_content_stream(file: UploadFile) -> AsyncIterator[bytes]:
            async def content_stream() -> AsyncIterator[bytes]:
                while content := await file.read(16 * 1024):
                    yield content

            return content_stream()

        await engine.store_documents(
            user=user,
            ids_and_streams=[
                (uuid.UUID(document.filename), make_content_stream(document))
                for document in documents
            ],
        )

    @router.get("/components")
    def get_components(_: UserDependency) -> schemas.Components:
        return engine.get_components()

    @router.post("/chats")
    async def create_chat(
        user: UserDependency,
        chat_creation: schemas.ChatCreation,
    ) -> schemas.Chat:
        return engine.create_chat(user=user, chat_creation=chat_creation)

    @router.get("/chats")
    async def get_chats(user: UserDependency) -> list[schemas.Chat]:
        return engine.get_chats(user=user)

    @router.get("/chats/{id}")
    async def get_chat(user: UserDependency, id: uuid.UUID) -> schemas.Chat:
        return engine.get_chat(user=user, id=id)

    @router.post("/chats/{id}/prepare")
    async def prepare_chat(user: UserDependency, id: uuid.UUID) -> schemas.Message:
        return await engine.prepare_chat(user=user, id=id)

    @router.post("/chats/{id}/answer")
    async def answer(
        user: UserDependency,
        id: uuid.UUID,
        prompt: Annotated[str, Body(..., embed=True)],
        stream: Annotated[bool, Body(..., embed=True)] = False,
    ) -> schemas.Message:
        message_stream = engine.answer_stream(user=user, chat_id=id, prompt=prompt)
        answer = await anext(message_stream)

        if not stream:
            content_chunks = [chunk.content async for chunk in message_stream]
            answer.content += "".join(content_chunks)
            return answer

        async def message_chunks() -> AsyncIterator[schemas.Message]:
            yield answer
            async for chunk in message_stream:
                yield chunk

        async def to_jsonl(
            models: AsyncIterator[pydantic.BaseModel],
        ) -> AsyncIterator[str]:
            async for model in models:
                yield f"{model.model_dump_json()}\n"

        return StreamingResponse(  # type: ignore[return-value]
            to_jsonl(message_chunks())
        )

    @router.delete("/chats/{id}")
    async def delete_chat(user: UserDependency, id: uuid.UUID) -> None:
        engine.delete_chat(user=user, id=id)

    return router
