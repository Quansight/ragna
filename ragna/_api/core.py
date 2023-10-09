import functools
from typing import Annotated
from uuid import UUID

import aiofiles
from fastapi import Depends, FastAPI, Form, HTTPException, UploadFile

import ragna

from ragna.core import Chat, LocalDocument, RagnaException, RagnaId

from . import schemas


def process_ragna_exception(afn):
    @functools.wraps(afn)
    async def wrapper(*args, **kwargs):
        try:
            return await afn(*args, **kwargs)
        except RagnaException as exc:
            if exc.http_detail is RagnaException.EVENT:
                detail = exc.event
            elif exc.http_detail is RagnaException.MESSAGE:
                detail = str(exc)
            else:
                detail = exc.http_detail
            raise HTTPException(
                status_code=exc.http_status_code, detail=detail
            ) from None
        except Exception:
            raise

    return wrapper


def api(rag):
    app = FastAPI()

    @app.get("/health")
    @process_ragna_exception
    async def health() -> str:
        return ragna.__version__

    async def _authorize_user(user: str) -> str:
        # FIXME: implement auth here
        return user

    UserDependency = Annotated[str, Depends(_authorize_user)]

    @app.get("/components")
    @process_ragna_exception
    async def get_components(_: UserDependency) -> schemas.Components:
        return schemas.Components(
            source_storages=list(rag.config.registered_source_storage_classes),
            assistants=list(rag.config.registered_assistant_classes),
        )

    @app.get("/document")
    @process_ragna_exception
    async def get_document_upload_info(
        user: UserDependency,
        name: str,
    ) -> schemas.DocumentUploadInfo:
        id = RagnaId.make()
        url, data, metadata = await rag.config.document_class.get_upload_info(
            config=rag.config, user=user, id=id, name=name
        )
        rag._add_document(user=user, id=id, name=name, metadata=metadata)
        return schemas.DocumentUploadInfo(
            url=url, data=data, document=schemas.Document(id=id, name=name)
        )

    @app.post("/document")
    @process_ragna_exception
    async def upload_document(
        token: Annotated[str, Form()], file: UploadFile
    ) -> schemas.Document:
        if not issubclass(rag.config.document_class, LocalDocument):
            raise HTTPException(
                status_code=400,
                detail="Ragna configuration does not support local upload",
            )

        user, id = rag.config.document_class._decode_upload_token(
            token, secret=rag.config.upload_token_secret
        )
        document = rag._get_document(user=user, id=id)

        document.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(document.path, "wb") as document_file:
            while content := await file.read(1024):
                await document_file.write(content)

        return schemas.Document(id=id, name=document.name)

    @app.post("/chats")
    @process_ragna_exception
    async def create_chat(
        *, user: UserDependency, chat_metadata: schemas.ChatMetadataCreate
    ) -> schemas.Chat:
        return schemas.Chat.from_core_chat(
            await rag.new_chat(
                user=user,
                name=chat_metadata.name,
                documents=chat_metadata.document_ids,
                source_storage=chat_metadata.source_storage,
                assistant=chat_metadata.assistant,
                **chat_metadata.params,
            )
        )

    @app.get("/chats")
    @process_ragna_exception
    async def get_chats(user: UserDependency) -> list[schemas.Chat]:
        return [schemas.Chat.from_core_chat(chat) for chat in rag._get_chats(user=user)]

    async def _get_id(id: UUID) -> RagnaId:
        return RagnaId.from_uuid(id)

    IdDependency = Annotated[RagnaId, Depends(_get_id)]

    async def _get_chat(*, user: UserDependency, id: IdDependency) -> Chat:
        return rag._get_chat(user=user, id=id)

    ChatDependency = Annotated[Chat, Depends(_get_chat, use_cache=False)]

    @app.get("/chats/{id}")
    @process_ragna_exception
    async def get_chat(chat: ChatDependency) -> schemas.Chat:
        return schemas.Chat.from_core_chat(chat)

    @app.post("/chats/{id}/start")
    @process_ragna_exception
    async def start_chat(chat: ChatDependency) -> schemas.Chat:
        return schemas.Chat.from_core_chat(await chat.start())

    @app.post("/chats/{id}/close")
    @process_ragna_exception
    async def close_chat(chat: ChatDependency) -> schemas.Chat:
        return schemas.Chat.from_core_chat(await chat.close())

    @app.post("/chats/{id}/answer")
    @process_ragna_exception
    async def answer(chat: ChatDependency, prompt: str) -> schemas.AnswerOutput:
        return schemas.AnswerOutput(
            message=schemas.Message.from_core_message(await chat.answer(prompt)),
            chat=schemas.Chat.from_core_chat(chat),
        )

    return app
