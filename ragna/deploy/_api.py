import uuid
from typing import Annotated, AsyncIterator, cast

import aiofiles
import pydantic
from fastapi import (
    APIRouter,
    Body,
    Depends,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import StreamingResponse

import ragna
import ragna.core
from ragna._compat import anext
from ragna.core._utils import default_user
from ragna.deploy import Config

from . import _schemas as schemas
from ._engine import Engine


def make_router(config: Config, engine: Engine) -> APIRouter:
    router = APIRouter(tags=["API"])

    def get_user() -> str:
        return default_user()

    UserDependency = Annotated[str, Depends(get_user)]

    # TODO: the document endpoints do not go through the engine, because they'll change
    #  quite drastically when the UI no longer depends on the API

    _database = engine._database

    @router.post("/document")
    async def create_document_upload_info(
        user: UserDependency,
        name: Annotated[str, Body(..., embed=True)],
    ) -> schemas.DocumentUpload:
        with _database.get_session() as session:
            document = schemas.Document(name=name)
            metadata, parameters = await config.document.get_upload_info(
                config=config, user=user, id=document.id, name=document.name
            )
            document.metadata = metadata
            _database.add_document(
                session, user=user, document=document, metadata=metadata
            )
            return schemas.DocumentUpload(parameters=parameters, document=document)

    # TODO: Add UI support and documentation for this endpoint (#406)
    @router.post("/documents")
    async def create_documents_upload_info(
        user: UserDependency,
        names: Annotated[list[str], Body(..., embed=True)],
    ) -> list[schemas.DocumentUpload]:
        with _database.get_session() as session:
            document_metadata_collection = []
            document_upload_collection = []
            for name in names:
                document = schemas.Document(name=name)
                metadata, parameters = await config.document.get_upload_info(
                    config=config, user=user, id=document.id, name=document.name
                )
                document.metadata = metadata
                document_metadata_collection.append((document, metadata))
                document_upload_collection.append(
                    schemas.DocumentUpload(parameters=parameters, document=document)
                )

            _database.add_documents(
                session,
                user=user,
                document_metadata_collection=document_metadata_collection,
            )
            return document_upload_collection

    # TODO: Add new endpoint for batch uploading documents (#407)
    @router.put("/document")
    async def upload_document(
        token: Annotated[str, Form()], file: UploadFile
    ) -> schemas.Document:
        if not issubclass(config.document, ragna.core.LocalDocument):
            raise HTTPException(
                status_code=400,
                detail="Ragna configuration does not support local upload",
            )
        with _database.get_session() as session:
            user, id = ragna.core.LocalDocument.decode_upload_token(token)
            document = _database.get_document(session, user=user, id=id)

            core_document = cast(
                ragna.core.LocalDocument, engine._to_core.document(document)
            )
            core_document.path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(core_document.path, "wb") as document_file:
                while content := await file.read(1024):
                    await document_file.write(content)

            return document

    @router.get("/components")
    def get_components(_: UserDependency) -> schemas.Components:
        return engine.get_components()

    @router.post("/chats")
    async def create_chat(
        user: UserDependency,
        chat_metadata: schemas.ChatMetadata,
    ) -> schemas.Chat:
        return engine.create_chat(user=user, chat_metadata=chat_metadata)

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
