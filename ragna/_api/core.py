import functools
import uuid
from typing import Annotated
from urllib.parse import urlsplit, urlunsplit

import aiofiles
from fastapi import Depends, FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import ragna
import ragna.core
from ragna.core import Config, Rag, RagnaException

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


def _get_cors_origins(config):
    origins = [config.api.url]

    components = urlsplit(config.api.url)

    def replace_hostname(hostname):
        return components._replace(netloc=f"{hostname}:{components.port}")

    # Since localhost is an alias for 127.0.0.1, we allow both so users and developers
    # don't need to worry about it.
    if components.hostname == "127.0.0.1":
        origins.append(urlunsplit(replace_hostname("localhost")))
    elif components.hostname == "localhost":
        origins.append(urlunsplit(replace_hostname("127.0.0.1")))

    return origins


def api(config: Config):
    rag = Rag(config)

    app = FastAPI(title="ragna", version=ragna.__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_cors_origins(config),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
            source_storages=[
                source_storage.display_name()
                for source_storage in config.rag.source_storages
            ],
            assistants=[
                assistant.display_name() for assistant in config.rag.assistants
            ],
        )

    database_url = config.api.database_url
    if database_url == "memory":
        database_url = "sqlite://"
    make_session = database.get_sessionmaker(database_url)

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
        url, data, metadata = await config.rag.document.get_upload_info(
            config=config, user=user, id=document.id, name=document.name
        )
        database.add_document(session, user=user, document=document, metadata=metadata)
        return schemas.DocumentUploadInfo(url=url, data=data, document=document)

    @app.post("/document")
    @process_ragna_exception
    async def upload_document(
        session: SessionDependency, token: Annotated[str, Form()], file: UploadFile
    ) -> schemas.Document:
        if not issubclass(rag.config.rag.document, ragna.core.LocalDocument):
            raise HTTPException(
                status_code=400,
                detail="Ragna configuration does not support local upload",
            )

        user, id = ragna.core.LocalDocument._decode_upload_token(
            token, secret=rag.config.api.upload_token_secret
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
        core_chat = rag.chat(
            documents=[
                rag.config.rag.document(
                    id=document.id,
                    name=document.name,
                    metadata=database.get_document(
                        session,
                        user=user,
                        id=document.id,
                    )[1],
                )
                for document in chat.metadata.documents
            ],
            source_storage=chat.metadata.source_storage,
            assistant=chat.metadata.assistant,
            user=user,
            chat_id=chat.id,
            chat_name=chat.metadata.name,
            **chat.metadata.params,
        )
        # FIXME: We need to reconstruct the previous messages here. Right now this is
        #  not needed, because the chat itself never accesses past messages. However,
        #  if we implement a chat history feature, i.e. passing past messages to
        #  the assistant, this becomes crucial.
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

        # Although we don't need the actual ragna.core.Chat object here,
        # we use it to validate the documents and metadata.
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
        session: SessionDependency, user: UserDependency, id: uuid.UUID
    ) -> schemas.Chat:
        return database.get_chat(session, user=user, id=id)

    @app.post("/chats/{id}/prepare")
    @process_ragna_exception
    async def prepare_chat(
        session: SessionDependency, user: UserDependency, id: uuid.UUID
    ) -> schemas.MessageOutput:
        chat = database.get_chat(session, user=user, id=id)

        core_chat = schema_to_core_chat(session, user=user, chat=chat)
        welcome = schemas.Message.from_core(await core_chat.prepare())
        chat.prepared = True
        chat.messages.append(welcome)

        database.update_chat(session, user=user, chat=chat)

        return schemas.MessageOutput(message=welcome, chat=chat)

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

        answer = schemas.Message.from_core(await core_chat.answer(prompt))
        chat.messages.append(answer)

        database.update_chat(session, user=user, chat=chat)

        return schemas.MessageOutput(message=answer, chat=chat)

    @app.delete("/chats/{id}")
    @process_ragna_exception
    async def delete_chat(
        session: SessionDependency, user: UserDependency, id: uuid.UUID
    ) -> None:
        database.delete_chat(session, user=user, id=id)

    return app
