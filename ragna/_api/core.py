import functools
from typing import Annotated

import aiofiles
from fastapi import Depends, FastAPI, Form, HTTPException, UploadFile

import ragna
import ragna.core

from ragna.core import Rag, RagnaException, RagnaId

from . import database, schemas


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


def api(config):
    rag = Rag(config)

    app = FastAPI()

    @app.get("/")
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

    make_session = database.get_sessionmaker(config.database_url)

    def get_session():
        session = make_session()
        try:
            yield session
        finally:
            session.close()

    SessionDependency = Annotated[database.Session, Depends(get_session)]

    @app.get("/document")
    @process_ragna_exception
    async def get_document_upload_info(
        session: SessionDependency,
        user: UserDependency,
        name: str,
    ) -> schemas.DocumentUploadInfo:
        document = schemas.Document(id=RagnaId.make(), name=name)
        url, data, metadata = await config.document_class.get_upload_info(
            config=config, user=user, id=document.id, name=document.name
        )
        database.add_document(session, user=user, document=document, metadata=metadata)
        return schemas.DocumentUploadInfo(url=url, data=data, document=document)

    @app.post("/document")
    @process_ragna_exception
    async def upload_document(
        session: SessionDependency, token: Annotated[str, Form()], file: UploadFile
    ) -> schemas.Document:
        if not issubclass(rag.config.document_class, ragna.core.LocalDocument):
            raise HTTPException(
                status_code=400,
                detail="Ragna configuration does not support local upload",
            )

        user, id = ragna.core.LocalDocument._decode_upload_token(
            token, secret=rag.config.upload_token_secret
        )
        document, metadata = database.get_document(session, user=user, id=id)

        core_document = ragna.core.LocalDocument(
            id=document.id, name=document.name, metadata=metadata
        )
        core_document.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(core_document.path, "wb") as document_file:
            while content := await file.read(1024):
                await document_file.write(content)

        return document

    @app.post("/chats")
    @process_ragna_exception
    async def create_chat(
        session: SessionDependency,
        user: UserDependency,
        chat_metadata: schemas.ChatMetadataCreate,
    ) -> schemas.Chat:
        documents = []
        core_documents = []
        for id in chat_metadata.document_ids:
            document, metadata = database.get_document(session, user=user, id=id)
            documents.append(document)
            core_documents.append(
                rag.config.document_class(id=id, name=document.name, metadata=metadata)
            )

        core_chat = await rag.new_chat(
            name=chat_metadata.name,
            documents=core_documents,
            source_storage=chat_metadata.source_storage,
            assistant=chat_metadata.assistant,
            **chat_metadata.params,
        )

        chat = schemas.Chat.from_core_chat(core_chat)
        database.add_chat(session, user=user, chat=chat)
        return chat

    @app.get("/chats")
    @process_ragna_exception
    async def get_chats(
        session: SessionDependency, user: UserDependency
    ) -> list[schemas.Chat]:
        return database.get_chats(session, user=user)

    @app.get("/chats/{id}")
    @process_ragna_exception
    async def get_chat(
        session: SessionDependency, user: UserDependency, id: RagnaId
    ) -> schemas.Chat:
        return database.get_chat(session, user=user, id=id)

    @app.put("/chats/{id}/start")
    @process_ragna_exception
    async def start_chat(
        session: SessionDependency, user: UserDependency, id: RagnaId
    ) -> schemas.Chat:
        return database.start_chat(session, user=user, id=id)

    @app.put("/chats/{id}/close")
    @process_ragna_exception
    async def close_chat(
        session: SessionDependency, user: UserDependency, id: RagnaId
    ) -> schemas.Chat:
        return database.start_chat(session, user=user, id=id)

    @app.post("/chats/{id}/answer")
    @process_ragna_exception
    async def answer(
        session: SessionDependency, user: UserDependency, id: RagnaId, prompt: str
    ) -> schemas.AnswerOutput:
        # we need to add the prompt as well as the output message

        core_chat = database.get_chat(session, user=user, id=id).to_core_chat(rag)
        return schemas.AnswerOutput(
            message=schemas.Message.from_core_message(await core_chat.answer(prompt)),
            chat=schemas.Chat.from_core_chat(core_chat),
        )

    return app
