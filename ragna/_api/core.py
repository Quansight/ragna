import functools
import uuid
from typing import Annotated

import aiofiles
from fastapi import Depends, FastAPI, Form, HTTPException, UploadFile

import ragna
import ragna.core

from ragna.core import Rag, RagnaException

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
        document = schemas.Document(name=name)
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

    def schema_to_core_chat(
        session, *, user: str, chat: schemas.Chat
    ) -> ragna.core.Chat:
        documents = []
        for document in chat.metadata.documents:
            _, metadata = database.get_document(session, user=user, id=document.id)
            documents.append(
                rag.config.document_class(
                    id=document.id, name=document.name, metadata=metadata
                )
            )

        core_chat = rag.chat(
            documents=documents,
            source_storage=chat.metadata.source_storage,
            assitant=chat.metadata.assistant,
            user=user,
            chat_id=chat.id,
            chat_name=chat.metadata.name,
            **chat.metadata.params,
        )
        # FIXME
        core_chat.messages = []
        core_chat._prepared = chat.prepared

        return core_chat

    @app.post("/chats")
    @process_ragna_exception
    async def create_chat(
        session: SessionDependency,
        user: UserDependency,
        chat_metadata: schemas.ChatMetadata,
    ) -> schemas.Chat:
        chat = schemas.Chat(metadata=chat_metadata)

        # Although we don't need the actual object here, we use this to validate the
        # documents and metadata
        schema_to_core_chat(session, user=user, chat=chat)

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
        session: SessionDependency, user: UserDependency, id: schemas.ID
    ) -> schemas.Chat:
        return database.get_chat(session, user=user, id=id)

    @app.put("/chats/{id}/prepare")
    @process_ragna_exception
    async def prepare_chat(
        session: SessionDependency, user: UserDependency, id: uuid.UUID
    ) -> schemas.MessageOutput:
        chat = database.get_chat(session, user=user, id=id)

        core_chat = schema_to_core_chat(session, user=user, chat=chat)
        welcome = await core_chat.prepare()
        chat.prepared = True
        chat.messages.append(schemas.Message.parse_obj(welcome))

        database.update_chat(session, user=user, chat=chat)

        return schemas.MessageOutput(message=answer, chat=chat)

    @app.post("/chats/{id}/answer")
    @process_ragna_exception
    async def answer(
        session: SessionDependency, user: UserDependency, id: uuid.UUID, prompt: str
    ) -> schemas.MessageOutput:
        chat = database.get_chat(session, user=user, id=id)
        chat.messages.append(
            schemas.Message(content=prompt, role=ragna.core.MessageRole.USER)
        )

        core_chat = schema_to_core_chat(session, user=user, chat=chat)
        answer = await core_chat.answer(prompt)
        chat.messages.append(schemas.Message.parse_obj(answer))

        database.update_chat(session, user=user, chat=chat)

        return schemas.MessageOutput(message=answer, chat=chat)

    return app
