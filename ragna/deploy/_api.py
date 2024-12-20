import uuid
from typing import Annotated, Any, AsyncIterator

import pydantic
from fastapi import APIRouter, Body, UploadFile
from fastapi.responses import StreamingResponse

from . import _schemas as schemas
from ._auth import UserDependency
from ._engine import Engine


def make_router(engine: Engine) -> APIRouter:
    router = APIRouter(tags=["API"])  # , dependencies=[UserDependency]

    @router.post("/documents")
    def register_documents(
        user: UserDependency, document_registrations: list[schemas.DocumentRegistration]
    ) -> list[schemas.Document]:
        return engine.register_documents(
            user=user.name, document_registrations=document_registrations
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
            user=user.name,
            ids_and_streams=[
                (uuid.UUID(document.filename), make_content_stream(document))
                for document in documents
            ],
        )

    @router.get("/components")
    def get_components() -> schemas.Components:
        return engine.get_components()

    @router.get("/corpuses")
    async def get_corpuses(source_storage: str | None = None) -> dict[str, list[str]]:
        return await engine.get_corpuses(source_storage)

    @router.get("/corpuses/metadata")
    async def get_corpus_metadata(
        _: UserDependency,
        source_storage: str | None = None,
        corpus_name: str | None = None,
    ) -> dict[str, dict[str, dict[str, tuple[str, list[Any]]]]]:
        return await engine.get_corpus_metadata(
            source_storage=source_storage, corpus_name=corpus_name
        )

    @router.post("/chats")
    async def create_chat(
        user: UserDependency,
        chat_creation: schemas.ChatCreation,
    ) -> schemas.Chat:
        return engine.create_chat(user=user.name, chat_creation=chat_creation)

    @router.get("/chats")
    async def get_chats(user: UserDependency) -> list[schemas.Chat]:
        return engine.get_chats(user=user.name)

    @router.get("/chats/{id}")
    async def get_chat(user: UserDependency, id: uuid.UUID) -> schemas.Chat:
        return engine.get_chat(user=user.name, id=id)

    @router.post("/chats/{id}/prepare")
    async def prepare_chat(user: UserDependency, id: uuid.UUID) -> schemas.Message:
        return await engine.prepare_chat(user=user.name, id=id)

    @router.post("/chats/{id}/answer")
    async def answer(
        user: UserDependency,
        id: uuid.UUID,
        prompt: Annotated[str, Body(..., embed=True)],
        stream: Annotated[bool, Body(..., embed=True)] = False,
    ) -> schemas.Message:
        message_stream = engine.answer_stream(user=user.name, chat_id=id, prompt=prompt)
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
        engine.delete_chat(user=user.name, id=id)

    return router
